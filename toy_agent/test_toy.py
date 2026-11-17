import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path('toy_agent/agent').resolve()))
from agent import ToyPlayer

def observation():
    return {'phase':'live','round_index':1,'match_tick':504,'seat':0,'side':'attack',
            'me':{'alive':True,'weapons':[{'id':'ak47','ammo':20,'reserve':30,'reload_until':0},None],
                  'active_slot':0,'x':0,'y':0,'z':0,'yaw':0,'pitch':0,'crouch':False,
                  'grounded':True,'blind_ticks':0},'visible':[]}

class ToyTests(unittest.TestCase):
    def test_roam_spins_and_moves(self):
        a=ToyPlayer().act(observation())
        self.assertEqual(a['yaw_rate'],1.0)
        self.assertAlmostEqual(a['move_forward']**2+a['move_right']**2,1.0)
        self.assertTrue(a['jump'])
    def test_enemy_stops_roaming_and_aims_head(self):
        o=observation();o['visible']=[{'x':10,'y':0,'z':0,'parts':['head','chest'],'crouch':False}]
        a=ToyPlayer().act(o)
        self.assertEqual(a.get('move_forward',0),0)
        self.assertFalse(a.get('jump',False))
        self.assertNotEqual(a['pitch_rate'],0)
        self.assertTrue(a['fire'])
    def test_resume_roaming_after_enemy_disappears(self):
        p=ToyPlayer();o=observation();o['visible']=[{'x':10,'y':0,'z':0,'parts':['head'],'crouch':False}]
        p.act(o);o['visible']=[]
        self.assertEqual(p.act(o)['yaw_rate'],1.0)
    def test_wanders_without_path_and_turns_when_stuck(self):
        p=ToyPlayer();o=observation()
        p.route=lambda *args: self.fail('Wandering should not choose a path')
        first=p.act(o)
        o['match_tick']+=61
        second=p.act(o)
        self.assertNotEqual(first['move_forward'],second['move_forward'])
        self.assertEqual(second['yaw_rate'],1.0)
    def test_switch_to_loaded_secondary(self):
        o=observation();o['me']['weapons']=[{'id':'ak47','ammo':0,'reserve':30}, {'id':'usp','ammo':10,'reserve':20}]
        o['visible']=[{'x':10,'y':0,'z':0,'parts':['head'],'crouch':False}]
        self.assertEqual(ToyPlayer().act(o),{'weapon_slot':1})

if __name__=='__main__': unittest.main()
