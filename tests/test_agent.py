import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fps_agent', ROOT / 'agent' / 'agent.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

def obs(side='attack', cash=1000):
    return {'phase':'buy','round_index':1,'round_tick':500,'match_tick':500,'seat':0,'side':side,
      'me':{'alive':True,'has_kit':False,'cash':cash,'weapons':[None,{'ammo':12,'reserve':24,'reload_until':0}],
            'armor':0,'x':0,'y':0,'z':0,'yaw':0,'pitch':0,'crouch':False,'blind_ticks':0,
            'grounded':True,'carrying_bomb':False},'bomb':{'state':'carried'},'visible':[]}

class PolicyTests(unittest.TestCase):
    def test_save_and_locked_full_buy(self):
        p=a.Player(); o=obs(cash=1000); self.assertEqual(p.buy(o),{})
        p=a.Player(); o=obs(cash=2500); self.assertEqual(p.buy(o),{'buy':'mac10'})
        p=a.Player(); o=obs(cash=3350); self.assertEqual(p.buy(o),{'buy':'ak47'})
        o['me']['cash']=650; o['me']['weapons'][0]={'ammo':30}; self.assertEqual(p.buy(o),{'buy':'armor'})
    def test_defender_purchases(self):
        p=a.Player(); o=obs('defend',3950); self.assertEqual(p.buy(o),{'buy':'m4a1'})
        o['me']['weapons'][0]={}; o['me']['cash']=1050; self.assertEqual(p.buy(o),{'buy':'armor'})
        o['me']['armor']=100; o['me']['cash']=400; self.assertEqual(p.buy(o),{'buy':'defusekit'})
    def test_threat_can_prefer_further_enemy(self):
        o=obs(); o['visible']=[{'x':-4,'y':0,'z':0},{'x':5,'y':0,'z':0}]
        self.assertEqual(a.Player().target(o)['x'],5)
    def test_danger_changes_route(self):
        p=a.Player(); p.nodes={'a':[0,0,0],'b':[5,0,0],'c':[10,0,0],'d':[5,4,0]}
        p.edges={'a':['b','d'],'b':['c'],'d':['c'],'c':[]}
        self.assertEqual(p.route([0,0,0],[10,0,0])[1],[5,0,0])
        self.assertEqual(p.route([0,0,0],[10,0,0],[5,0,0])[1],[5,4,0])
    def test_preaim_preserves_travel_vector(self):
        p=a.Player(); p.last_seen_enemy=[0,-10,0]; p.last_seen_tick=500
        o=obs(); o['phase']='live'; action=p.move(o,[10,0,0],{})
        self.assertGreater(action['move_forward'],0); self.assertGreater(action['yaw_rate'],0)
    def test_round_transition(self):
        p=a.Player(); o=obs(cash=1000); self.assertEqual(p.buy(o),{})
        o['round_index']=2; o['me']['cash']=4000; self.assertEqual(p.buy(o),{'buy':'ak47'})
    def test_force_buy_and_awp(self):
        p=a.Player(); o=obs(cash=1500); o.update(team=0, round_wins=[5,12], win_target=13)
        self.assertEqual(p.buy(o), {'buy':'mac10'})
        p=a.Player(); o=obs(cash=7000); self.assertEqual(p.buy(o), {'buy':'awp'})
        p=a.Player(); o=obs(cash=7000); o['seat']=1; self.assertEqual(p.buy(o), {'buy':'ak47'})
    def test_anonymous_sounds_ignored(self):
        p=a.Player();o=obs();o['sounds']=[{'type':'footstep','direction':'left','distance_band':'near'}]
        p.listen(o);self.assertIsNone(p.sound_yaw)
    def test_awp_scopes_and_needs_zoom(self):
        p=a.Player(); o=obs(); o['phase']='live'; o['visible']=[{'x':10,'y':0,'z':0,'parts':['chest'],'crouch':False}]
        gun={'id':'awp','ammo':5,'reload_until':0}; act=p.combat(o,{'weapon_slot':0},gun)
        self.assertEqual(act['zoom_level'],1); self.assertFalse(act['fire'])
    def test_automatic_bomb_pickup(self):
        p=a.Player(); p.sites=[{'center':[10,0,0],'radius':4}]
        o=obs(); o['phase']='live'; o['bomb']={'state':'world','position':[0.5,0,0],'id':'bomb'}
        self.assertNotEqual(p.act(o).get('use'), 'pickup')
    def test_valuable_weapon_fights_unless_urgent(self):
        p=a.Player(); p.sites=[{'center':[10,0,0],'radius':4}]
        o=obs('defend'); o.update(phase='live',team=0,round_wins=[5,5],win_target=13)
        o['me']['weapons'][0]={'id':'ak47','ammo':20,'reserve':30,'reload_until':0}
        o['me']['active_slot']=0; o['bomb']={'state':'planted','position':[1,0,0], 'fuse_end_tick':2000}
        o['visible']=[{'x':1,'y':0,'z':0,'parts':['chest'],'crouch':False}]
        self.assertNotIn('use',p.act(o))
        o['round_wins']=[5,12]; self.assertEqual(p.act(o)['use'],'defuse')
        o['round_wins']=[5,5]; o['bomb']['fuse_end_tick']=1100
        self.assertEqual(p.act(o)['use'],'defuse')
    def test_reload_then_switch_when_enemy_appears(self):
        p=a.Player(); p.sites=[{'center':[10,0,0],'radius':4}]
        o=obs(); o['phase']='live'; o['me']['weapons'][0]={'id':'ak47','ammo':4,'reserve':30,'reload_until':0}
        o['me']['active_slot']=0; self.assertTrue(p.act(o)['reload'])
        o['visible']=[{'x':4,'y':0,'z':0,'parts':['chest'],'crouch':False}]
        switched=p.act(o); self.assertEqual(switched['weapon_slot'],1); self.assertNotIn('reload',switched)
        o['me']['active_slot']=1; self.assertIn('fire',p.act(o))
        o['visible']=[]; self.assertEqual(p.act(o)['weapon_slot'],0)
        o['me']['active_slot']=0; self.assertTrue(p.act(o)['reload'])
    def test_no_reload_with_no_reserve_or_during_switch(self):
        p=a.Player(); p.sites=[{'center':[10,0,0],'radius':4}]; o=obs(); o['phase']='live'
        o['me']['weapons'][0]={'id':'ak47','ammo':4,'reserve':0,'reload_until':0}; o['me']['active_slot']=0
        self.assertNotIn('reload',p.act(o))
        o['me']['weapons'][0]['reserve']=30; o['me']['active_slot']=1
        self.assertNotIn('reload',p.act(o))
    def test_cover_selection_and_center_fallback(self):
        p=a.Player(); site={'id':'A','center':[0,0,0],'radius':4}
        p.nodes={'site':[0,0,0], 'near_wall':[3,2,0]}
        self.assertEqual(p.defensive_position(site,0),[0,0,0])
        p.cover_cache={}; p.cover_boxes=[{'x':3,'y':0,'z':0,'w':2,'d':2,'h':2}]
        self.assertEqual(p.defensive_position(site,0),[3,2,0])
    def test_flash_prime_release_and_once_per_round(self):
        p=a.Player(); o=obs(); o['phase']='live'; o['me']['throwable_kinds']=['flashbang']; o['me']['throw_ready']=None
        o['visible']=[]
        p.flash_safe=lambda o,approach: True
        self.assertEqual(p.utility_action(o,[15,0,0])['throw_state'],'prime')
        o['match_tick']+=3; self.assertEqual(p.utility_action(o,[15,0,0])['throw_state'],'release')
        self.assertIsNone(p.utility_action(o,[15,0,0]))
    def test_buy_flash_once(self):
        p=a.Player(); o=obs(cash=4000); o['me']['weapons'][0]={'id':'ak47','ammo':30}; o['me']['armor']=100
        self.assertEqual(p.buy(o),{'buy':'flashbang'}); self.assertEqual(p.buy(o),{'buy':'smokegrenade'}); self.assertEqual(p.buy(o),{'buy':'hegrenade'}); self.assertEqual(p.buy(o),{})
    def test_defender_moves_toward_site_from_spawn(self):
        p=a.Player(); p.sites=[{'id':'A','center':[10,0,0],'radius':4}]
        o=obs('defend'); o['phase']='live'; o['round_tick']=360
        self.assertNotEqual(p.act(o).get('move_forward',0),0)
    def test_cover_route_prefers_covered_alternative(self):
        p=a.Player(); p.nodes={'a':[0,0,0],'b':[5,0,0],'c':[10,0,0],'d':[5,2,0]}
        p.edges={'a':['b','d'],'b':['c'],'d':['c'],'c':[]}
        wall={'x':5,'y':4,'z':0,'w':10,'d':1,'h':2}; p.cover_grid={(0,0):[wall],(-1,0):[wall]}
        self.assertEqual(p.route([0,0,0],[10,0,0])[1],[5,2,0])
    def test_peek_geometry_forward_and_backward(self):
        p=a.Player();p.path=[[5,0,0],[8,0,0]];p.goal=[8,0,0]
        box={'x':0,'y':1,'z':0,'w':2,'d':2,'h':2};p.cover_grid={(0,0):[box]}
        o=obs();o['phase']='live'; first=p.move(o,[8,0,0],{})
        self.assertGreater(first['move_forward'],0)
        o['match_tick']+=6;o['visible']=[{'x':5,'y':0,'z':0,'parts':['chest'],'crouch':False}]
        self.assertLess(p.peek_action(o,{})['move_forward'],0)
        o['match_tick']+=12;self.assertIsNone(p.peek_action(o,{}))
    def test_no_peek_for_navigation_turn_without_geometry(self):
        p=a.Player();p.path=[[2,0,0],[2,10,0]];p.goal=[2,10,0];o=obs();o['phase']='live'
        self.assertNotEqual(p.move(o,[2,10,0],{}).get('move_forward',0),0)
    def test_occupied_zone_discount_and_threat_priority(self):
        p=a.Player();p.spawn_points={'attack':[[10,0,0,0]]};p.landmarks={'A':[10,0,0],'B':[0,10,0]}
        site={'center':[0,0,0]};o=obs('defend');o['teammates']=[{'alive':True,'zone':'A'}]
        self.assertAlmostEqual(p.watch_heading(o,site),-3.141592653589793/2)
        p.last_seen_enemy=[10,0,0];p.last_seen_tick=o['match_tick'];out=p.hold(o,{},site)
        self.assertEqual(out['yaw_rate'],0)
    def test_defender_rotates_towards_dropped_bomb(self):
        p=a.Player(); p.sites=[{'id':'A','center':[20,0,0],'radius':4},{'id':'B','center':[0,20,0],'radius':4}]
        o=obs('defend');o.update(phase='live',round_tick=700,round_index=0);o['bomb']={'state':'world','position':[20,0,0]}
        out=p.act(o); self.assertGreater(out.get('move_forward',0),0)
    def test_planted_known_position_overrides_site(self):
        p=a.Player();p.sites=[{'id':'A','center':[20,0,0],'radius':4},{'id':'B','center':[0,20,0],'radius':4}]
        o=obs('defend');o.update(phase='live',round_tick=500,round_index=0);o['bomb']={'state':'planted','position':[20,0,0]}
        self.assertGreater(p.act(o).get('move_forward',0),0)
    def test_rebalance_only_if_all_teammates_on_assigned_site(self):
        p=a.Player();p.sites=[{'id':'A','center':[20,0,0],'radius':4},{'id':'B','center':[0,20,0],'radius':4}]
        o=obs('defend');o.update(phase='live',round_tick=1800,round_index=0);o['bomb']={'state':'unknown'}
        self.assertEqual(p.uncovered_site(o,p.sites[0])['id'],'A')
        o['teammates']=[{'seat':1,'alive':True,'zone':'A'},{'seat':2,'alive':True,'zone':'A'}]
        p.uncovered_site(o,p.sites[0]);o['match_tick']+=183
        self.assertEqual(p.uncovered_site(o,p.sites[0])['id'],'B')
        o['teammates'][1]['zone']='B';self.assertEqual(p.uncovered_site(o,p.sites[0])['id'],'A')
    def test_optional_smoke_and_fire_at_corner(self):
        for kind in ('smokegrenade','molotov','incgrenade'):
            p=a.Player();o=obs();o['me']['throwable_kinds']=[kind];p.peek_until=600
            p.utility_safe=lambda o,approach,kind: True
            prime=p.utility_action(o,[15,0,0]);self.assertEqual((prime['throw'],prime['throw_state']),(kind,'prime'))
            o['match_tick']+=3;release=p.utility_action(o,[15,0,0]);self.assertEqual((release['throw'],release['throw_state']),(kind,'release'))
    def test_alert_on_damage_and_friendly_death(self):
        p=a.Player();p.nodes={'cover':[3,2,0]}; b={'x':3,'y':0,'z':0,'w':2,'d':2,'h':2};p.cover_grid={(0,0):[b]}
        o=obs();o['phase']='live';o['me']['hp']=100;o['teammates']=[{'seat':1,'alive':True}];p.update_alert(o)
        o['match_tick']+=3;o['me']['hp']=80;p.update_alert(o);self.assertEqual(p.alert_cover,[3,2,0]);self.assertGreater(p.alert_until,o['match_tick'])
        o['match_tick']+=3;o['teammates'][0]['alive']=False;p.update_alert(o);self.assertGreater(p.alert_until,o['match_tick'])
    def test_no_flash_in_direct_fight(self):
        p=a.Player();o=obs();o['me']['throwable_kinds']=['flashbang'];o['visible']=[{'x':15,'y':0,'z':0,'parts':['chest'],'crouch':False}]
        self.assertIsNone(p.utility_action(o,[15,0,0]))
    def test_spawn_aim_avoids_backwards_waypoint(self):
        p=a.Player();p.spawn_points={'attack':[[0,0,0,0]],'defend':[[100,0,0,0]]}
        o=obs();o['phase']='live';o['round_tick']=500
        self.assertAlmostEqual(p.travel_aim(o,[0,0,0],[-5,0,0],[-5,0,0]),0)
        o['round_tick']=2400
        self.assertAlmostEqual(abs(p.travel_aim(o,[0,0,0],[-5,0,0],[-5,0,0])),3.141592653589793)
    def test_stuck_area_penalized(self):
        p=a.Player();p.nodes={'a':[0,0,0],'b':[5,0,0],'c':[10,0,0],'d':[5,2,0]}
        p.edges={'a':['b','d'],'b':['c'],'d':['c'],'c':[]}
        p.blocked_point=[5,0,0]
        self.assertEqual(p.route([0,0,0],[10,0,0])[1],[5,2,0])
    def test_defensive_position_can_be_outside_site(self):
        p=a.Player();site={'id':'A','center':[0,0,0],'radius':4}
        p.nodes={'safe':[10,2,0]};p.cover_boxes=[{'x':10,'y':0,'z':0,'w':2,'d':2,'h':2}]
        self.assertEqual(p.defensive_position(site,0),[10,2,0])
    def test_ambiguous_sound_ignored_near_spawn(self):
        p=a.Player();p.spawn_points={'attack':[[0,0,0,0]],'defend':[[100,0,0,0]]}
        o=obs();o['phase']='live';o['sounds']=[{'type':'footstep','direction':'left','distance_band':'unknown'}]
        p.listen(o);self.assertIsNone(p.sound_yaw)
    def test_self_sound_ignored(self):
        p=a.Player();o=obs();o['sounds']=[{'type':'footstep','direction':'self','distance_band':'self'}]
        p.listen(o);self.assertIsNone(p.sound_yaw)
    def test_flash_gate_and_away_turn(self):
        p=a.Player();o=obs();o['phase']='live';o['me']['throwable_kinds']=['flashbang']; target=[15,0,0]
        self.assertIsNone(p.utility_action(o,target))
        p.near_building_corner=lambda pos: True;p.cover_toward=lambda pos,point: True
        o['teammates']=[{'seat':1,'alive':True,'zone':'A'}];p.landmarks={'A':[15,0,0]}
        self.assertIsNone(p.utility_action(o,target))
        p.landmarks={'A':[100,100,0]}
        self.assertEqual(p.utility_action(o,target)['throw_state'],'prime')
        o['match_tick']+=3;self.assertEqual(p.utility_action(o,target)['throw_state'],'release')
        self.assertGreater(p.flash_turn_until,o['match_tick'])
        self.assertNotEqual(p.flash_avoid(o,{})['yaw_rate'],0)
    def test_flash_cancels_if_team_approaches_or_enemy_visible(self):
        p=a.Player();o=obs();o['me']['throwable_kinds']=['flashbang'];target=[15,0,0]
        p.near_building_corner=lambda pos:True;p.cover_toward=lambda pos,point:True
        self.assertEqual(p.utility_action(o,target)['throw_state'],'prime')
        o['match_tick']+=3;o['teammates']=[{'alive':True,'zone':'unknown'}]
        self.assertEqual(p.utility_action(o,target)['throw_state'],'cancel')
    def test_attacker_escorts_observed_carrier(self):
        p=a.Player();p.sites=[{'id':'A','center':[40,0,0],'radius':4}]
        o=obs();o.update(phase='live',round_index=0,round_tick=500)
        o['bomb']={'state':'held','carrier':1,'position':[0,20,0]}
        out=p.act(o);self.assertGreater(out.get('move_right',0),0)
    def test_defender_moves_toward_seen_carrier(self):
        p=a.Player();p.sites=[{'id':'A','center':[0,30,0],'radius':4}]
        o=obs('defend');o.update(phase='live',round_index=0,round_tick=500)
        o['bomb']={'state':'held','carrier':9,'position':[20,0,0]}
        self.assertGreater(p.act(o).get('move_forward',0),0)
    def test_defend_weak_site_after_stability(self):
        p=a.Player();p.sites=[{'id':'A','center':[20,0,0]},{'id':'B','center':[0,20,0]}]
        o=obs('defend');o['teammates']=[{'alive':True,'zone':'A'},{'alive':True,'zone':'A'}]
        self.assertEqual(p.weak_defensive_site(o,p.sites[0])['id'],'A')
        o['match_tick']+=183;self.assertEqual(p.weak_defensive_site(o,p.sites[0])['id'],'B')
        o['visible']=[{'x':20,'y':0},{'x':20,'y':1},{'x':20,'y':2},{'x':20,'y':3}]
        self.assertEqual(p.weak_defensive_site(o,p.sites[1])['id'],'B')
        o['match_tick']+=183;self.assertEqual(p.weak_defensive_site(o,p.sites[1])['id'],'A')
    def test_late_fuse_does_not_trigger_retreat(self):
        for side in ('attack', 'defend'):
            p=a.Player();p.sites=[{'id':'A','center':[10,0,0],'radius':4}]
            p.spawn_points={side:[[-100,0,0,0]]}
            o=obs(side);o['phase']='live';o['me']['x']=9
            o['bomb']={'state':'planted','position':[10,0,0],'fuse_end_tick':501}
            out=p.act(o)
            if side == 'defend':
                self.assertEqual(out.get('use'),'defuse')
            else:
                self.assertGreaterEqual(out.get('move_forward',0),0)
    def test_all_utilities_reject_unknown_teammate_zone(self):
        p=a.Player();p.near_building_corner=lambda pos:True;o=obs();o['teammates']=[{'alive':True,'zone':'unknown'}]
        for kind in ('smokegrenade','hegrenade','molotov','incgrenade'):
            self.assertFalse(p.utility_safe(o,[15,0,0],kind))
    def test_expensive_gun_cautious_in_contested_area(self):
        p=a.Player();p.spawn_points={'attack':[[0,0,0,0]],'defend':[[100,0,0,0]]}
        o=obs();o['phase']='live';o['me']['x']=50;o['me']['weapons'][0]={'id':'awp','ammo':5,'reserve':10}
        out=p.move(o,[70,0,0],{});self.assertAlmostEqual(out['move_forward'],0.55)
    def test_team_assignments(self):
        p=a.Player(); p.sites=[{'center':[10,0,0], 'radius':4},{'center':[-10,0,0], 'radius':4}]
        o=obs(); one=p.choose_site(o); o['seat']=1; self.assertEqual(p.choose_site(o),one)
        o['side']='defend'; other=p.choose_site(o); o['seat']=0; self.assertNotEqual(p.choose_site(o),other)
    def test_objective_and_threat(self):
        p=a.Player(); p.sites=[{'center':[10,0,0],'radius':4}]
        o=obs('defend'); o['phase']='live'; o['bomb']={'state':'planted','position':[1,0,0]}
        self.assertEqual(p.act(o)['use'],'defuse')
        o['visible']=[{'x':1,'y':0,'z':0,'parts':['chest'],'crouch':False}]
        self.assertEqual(p.act(o)['use'],'defuse')

if __name__ == '__main__': unittest.main()
