"""Experimental roaming spinner for AGX FPS; independent of tactical v12."""
import math
import gc
from navigation import Player, angle, clip


class ToyPlayer(Player):
    def __init__(self):
        super().__init__()
        self.roam_heading = None
        self.heading_tick = 0
        self.turn_count = 0
        self.roam_anchor = None
        self.roam_anchor_tick = 0

    def roam(self, o, action):
        m, tick = o['me'], o['match_tick']
        pos = [m['x'], m['y'], m['z']]
        if self.roam_anchor is None or math.dist(pos[:2], self.roam_anchor[:2]) > 1.0:
            self.roam_anchor, self.roam_anchor_tick = pos, tick
        stuck = tick - self.roam_anchor_tick > 60
        if self.roam_heading is None:
            self.roam_heading, self.heading_tick = m['yaw'], tick
        elif stuck or tick - self.heading_tick >= 240:
            self.turn_count += 1
            # A larger turn helps escape walls; smaller changes vary free roaming.
            self.roam_heading = angle(self.roam_heading + (2.4 if stuck else 0.8) * (1 if self.turn_count % 2 else -1))
            self.heading_tick = tick
            self.roam_anchor, self.roam_anchor_tick = pos, tick
        heading = angle(self.roam_heading - m['yaw'])
        action.update(move_forward=math.cos(heading), move_right=-math.sin(heading),
                      yaw_rate=1.0, pitch_rate=clip(-m['pitch']/0.1), walk=False,
                      jump=bool(m.get('grounded') and (tick // 3) % 2 == 0))
        return action

    def engage(self, o, action, gun):
        m = o['me']
        enemy = self.target(o)
        dx, dy = enemy['x']-m['x'], enemy['y']-m['y']
        parts = enemy.get('parts', [])
        part = next((p for p in ('head', 'chest', 'abdomen') if p in parts), None)
        if part is None:
            return action
        height = {'head':1.64, 'chest':1.18, 'abdomen':0.88}[part]
        if enemy.get('crouch'):
            height *= 0.6
        eye = 0.95 if m.get('crouch') else 1.62
        punch = gun.get('aim_punch', {}) or {}
        yaw = angle(math.atan2(-dy, dx) - m['yaw'] - 2*punch.get('yaw', 0))
        pitch = math.atan2(enemy['z']+height-m['z']-eye, max(0.1, math.hypot(dx, dy))) - m['pitch'] - 2*punch.get('pitch', 0)
        reload_until = gun.get('reload_until', 0)
        ready = gun.get('ammo', 0) > 0 and (not isinstance(reload_until, (int, float)) or reload_until <= o['match_tick'])
        gun_id = gun.get('id')
        semi = action['weapon_slot'] == 1 or gun_id in ('awp', 'ssg08', 'nova')
        trigger = not semi or (o['match_tick'] // 3) % 4 == 0
        if gun_id in ('awp', 'ssg08'):
            action['zoom_level'] = 1
            ready = ready and m.get('zoom_level', 0) > 0
        action.update(yaw_rate=clip(yaw/0.15), pitch_rate=clip(pitch/0.1),
                      fire=bool(ready and trigger and abs(yaw)<0.04 and abs(pitch)<0.04))
        return action

    def act(self, o):
        if self.round != o['round_index']:
            self.round = o['round_index']
            self.roam_heading, self.roam_anchor, self.turn_count = None, None, 0
        m = o['me']
        if not m['alive'] or o['phase'] not in ('buy', 'live'):
            return {}
        if o['phase'] == 'buy':
            return self.buy(o)
        slot = self.select_weapon(o)
        gun = m['weapons'][slot]
        action = {'weapon_slot':slot}
        threat = bool(o.get('visible') and not m.get('blind_ticks'))
        if threat:
            if not gun or m.get('active_slot', slot) != slot:
                return action
            if gun.get('ammo', 0) <= 0 and gun.get('reserve', 0) > 0:
                action['reload'] = True
                return action
            return self.engage(o, action, gun)
        if gun and m.get('active_slot', slot) == slot and self.low_ammo(gun) and gun.get('reserve', 0)>0 and gun.get('reload_until', 0) <= o['match_tick']:
            action['reload'] = True
        return self.roam(o, action)


_player = ToyPlayer()

def init(context):
    global _player
    gc.disable()
    _player = ToyPlayer()

def act(observation):
    return _player.act(observation)
