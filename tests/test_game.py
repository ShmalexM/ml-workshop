"""Hero rules and HTTP workflows use only seeded RNGs and disposable databases."""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import game
from courses import COURSES, LESSONS
from library import import_book
from book_fixture import make_epub
from server_fixture import server_token

# Finishing everything earns one chest and one battle per lesson and per path.
EARNED = len(LESSONS) + len(COURSES)

STAMP = '2026-10-05T22:00:00+00:00'


def progress_fixture():
    return dict(completed={}, projects=[], projectState={}, readingState={}, guides=[])


def full_progress():
    progress = progress_fixture()
    progress['completed'] = {l['id']: dict(at=STAMP, xp=l['xp']) for l in LESSONS}
    return progress


class LowestRoll(random.Random):
    """Force basic rarity and the first slot to exercise pity and chest floors."""
    def choices(self, population, weights=None, *, cum_weights=None, k=1):
        return [population[0]] * k


class LootTests(unittest.TestCase):
    def test_campaign_names_and_health_scaling(self):
        expected = [
            ('Blighted Outskirts', 'Grimpelt the Alpha'),
            ('The Bonefields', 'Bonelord Varak'),
            ('Silkweb Hollow', 'Broodmother Ixis'),
            ('Drowned Crypt', 'Stitchgut the Abomination'),
            ('Ember Wastes', 'Pyrelord Akkar'),
            ('Hellhound Kennels', 'Cerberax the Twin-Maw'),
            ('The Void Rift', 'The Unmaker'),
            ('Brimstone Foundry', 'Slagheart Colossus'),
            ('Shadow Citadel', 'Malachar the Dread'),
            ('The Burning Gate', 'Azgaroth, Lord of Cinders'),
        ]
        for stage, names in enumerate(expected, 1):
            self.assertEqual(game.stage_names(stage), names)
            self.assertEqual(game.boss_hp(stage), round(3000 * 1.7**(stage - 1)))
        for stage in range(11, 31):
            boss = ('Tyrant', 'Behemoth', 'Herald', 'Warden', 'Devourer')[(stage - 11) % 5]
            self.assertEqual(game.stage_names(stage), (f'The Abyss · Depth {stage - 10}',
                                                      'Abyssal ' + boss))
            self.assertEqual(game.boss_hp(stage), round(game.boss_hp(10) * 1.25**(stage - 10)))
        self.assertEqual(len(game.CAMPAIGN_STAGES), 10)

    def test_every_class_all_tiers(self):
        expected_keys = {'primary', 'stamina', 'crit', 'haste', 'mastery',
                         'versatility', 'armor', 'damage'}
        for index, cls in enumerate(game.CLASSES):
            rng = random.Random(4700 + index)
            kit = game.starter_kit(cls['id'], rng, STAMP)
            equipment = {i['slot']: i for i in kit}
            luck = dict(sinceEpic=0, sinceLegendary=0)
            total = 0
            for tier in range(1, 6):
                for _ in range(100):
                    items, luck = game.roll_chest(cls['id'], tier, equipment, set(), luck,
                                                  rng, 'test:source', STAMP)
                    total += len(items)
                    self.assertIn(len(items), {1: [1], 2: [1, 2], 3: [1, 2],
                                               4: [2], 5: [2, 3]}[tier])
                    if tier >= 4:
                        self.assertTrue(any(i['rarity'] in ('rare', 'epic', 'legendary')
                                            for i in items))
                    for item in items:
                        slot, base, rarity = item['slot'], item['base'], item['rarity']
                        with self.subTest(cls=cls['id'], tier=tier, slot=slot, base=base):
                            self.assertEqual(set(item['stats']), expected_keys)
                            self.assertTrue(all(type(v) is int and v >= 0
                                                for v in item['stats'].values()))
                            self.assertEqual(item['primaryStat'], cls['primary'])
                            self.assertEqual(item['twoHand'], base in game.TWO_HAND)
                            self.assertTrue(0 <= item['seed'] <= 2**31 - 1)
                            self.assertEqual(item['source'], 'test:source')
                            self.assertEqual(item['obtainedAt'], STAMP)
                            lo, hi = game.TIER_BY_ID[tier]['ilvl']
                            bonus = game.RARITY_BONUS[rarity]
                            self.assertTrue(lo + bonus <= item['ilvl'] <= hi + bonus)
                            if slot in game.ARMOR_SLOTS:
                                self.assertEqual(base, cls['armor'])
                            elif slot == 'back':
                                self.assertEqual(base, 'cloak')
                            else:
                                self.assertIn(base, cls[slot])
                            if cls['id'] == 'hunter':
                                self.assertNotEqual(slot, 'offhand')
                            if base == 'wand' or item['twoHand']:
                                self.assertEqual(slot, 'mainhand')
                            if base in ('shield', 'tome', 'orb'):
                                self.assertEqual(slot, 'offhand')
                                self.assertEqual(item['stats']['damage'], 0)
                            if rarity == 'legendary':
                                self.assertEqual(set(item['effect']), {'id', 'name', 'text'})
                                self.assertIn(item['effect'], game.EFFECTS)
                                self.assertTrue(item['flavor'])
                            else:
                                self.assertIsNone(item['effect'])
                                self.assertEqual(bool(item['flavor']), rarity == 'epic')
                            if rarity == 'common':
                                stat = game.ANIMALS[item['name'].rsplit(' ', 1)[1]]
                                nonzero = {s for s in game.SECONDARIES if item['stats'][s]}
                                self.assertEqual(nonzero, {stat})
            self.assertGreaterEqual(total, 400)

    def test_stat_formulas(self):
        cases = [
            ('warrior', 'chest', 'plate', 1., 2., 0),
            ('rogue', 'legs', 'leather', .9, 1., 0),
            ('hunter', 'head', 'mail', .8, 1.4, 0),
            ('mage', 'hands', 'cloth', .65, .6, 0),
            ('mage', 'back', 'cloak', .5, .6, 0),
            ('warrior', 'mainhand', 'greatsword', 1., 0, 2.3),
            ('hunter', 'mainhand', 'bow', 1., 0, 2.1),
            ('rogue', 'mainhand', 'dagger', .65, 0, 1.2),
            ('warrior', 'mainhand', 'sword', .65, 0, 1.35),
            ('mage', 'mainhand', 'wand', .65, 0, 1.4),
            ('warrior', 'offhand', 'shield', .5, 3.2, 0),
            ('mage', 'offhand', 'orb', .5, 0, 0),
            ('paladin', 'offhand', 'tome', .5, 0, 0),
        ]
        for cid, slot, base, weight, armor, damage in cases:
            for index, rarity in enumerate(game.RARITY_IDS):
                with self.subTest(base=base, rarity=rarity):
                    item = game.generate_item(cid, slot, base, rarity, 47, random.Random(10))
                    stats = item['stats']
                    budget = 47 * game.RARITY_MULT[rarity] * weight
                    self.assertEqual(stats['primary'], round(budget * (.75 if base in
                                                                       ('tome', 'orb') else .55)))
                    self.assertEqual(stats['stamina'], round(budget * .80))
                    self.assertEqual(stats['damage'], round(47 * damage * game.RARITY_MULT[rarity]))
                    armor_weight = 1. if base == 'shield' else weight
                    self.assertEqual(stats['armor'], round(47 * armor * armor_weight * (1 + .08 * index)))
                    secondaries = sorted(stats[s] for s in game.SECONDARIES if stats[s])
                    factors = (.30, .22, .18)[:game.SECONDARY_COUNT[rarity]]
                    self.assertEqual(secondaries, sorted(round(budget * f) for f in factors))

    def test_starter_kits_for_all_classes(self):
        for cls in game.CLASSES:
            items = game.starter_kit(cls['id'], random.Random(10), STAMP)
            expected = ['chest', 'legs', 'feet', 'mainhand']
            if len(game.STARTER_WEAPONS[cls['id']]) == 2:
                expected.append('offhand')
            self.assertEqual([i['slot'] for i in items], expected)
            for item in items:
                self.assertEqual(item['rarity'], 'basic')
                self.assertEqual(item['ilvl'], 5)
                self.assertEqual(item['source'], 'starter')
                self.assertTrue(item['name'].startswith("Recruit's "))
                game.validate_usable(cls['id'], item)

    def test_smart_slot_weights(self):
        equipment = dict(chest={'ilvl': 8}, feet={'ilvl': 90},
                         mainhand={'ilvl': 8, 'twoHand': True})
        weights = game.slot_weights('warrior', 3, equipment, ['head'])
        self.assertAlmostEqual(weights['head'], 2.5 * .15)
        self.assertAlmostEqual(weights['chest'], 1.6)
        self.assertAlmostEqual(weights['feet'], 1.)
        self.assertAlmostEqual(weights['mainhand'], 1.6 * 1.3)
        self.assertAlmostEqual(weights['offhand'], 2.5 * .7 * .4)
        self.assertNotIn('offhand', game.slot_weights('hunter', 3, {}))

    def test_pity_thresholds_weights_and_floor(self):
        rng = LowestRoll(1)
        luck = dict(sinceEpic=38, sinceLegendary=88)
        rarity, luck = game.roll_rarity(1, luck, rng)
        self.assertEqual((rarity, luck), ('basic', dict(sinceEpic=39, sinceLegendary=89)))
        rarity, luck = game.roll_rarity(1, luck, rng)
        self.assertEqual((rarity, luck), ('legendary', dict(sinceEpic=0, sinceLegendary=0)))
        rarity, luck = game.roll_rarity(1, dict(sinceEpic=39, sinceLegendary=40), rng)
        self.assertEqual((rarity, luck), ('epic', dict(sinceEpic=0, sinceLegendary=41)))
        with patch.object(rng, 'choices', return_value=['legendary']) as choose:
            rarity, luck = game.roll_rarity(2, dict(sinceEpic=8, sinceLegendary=10), rng)
            self.assertEqual(choose.call_args.kwargs['weights'], [42, 40, 15, 4.8, .7])
            self.assertEqual(luck, dict(sinceEpic=0, sinceLegendary=0))
        original = dict(sinceEpic=0, sinceLegendary=0)
        items, luck = game.roll_chest('warrior', 4, {}, set(), original, rng)
        self.assertEqual([i['rarity'] for i in items], ['rare', 'basic'])
        self.assertEqual(luck, dict(sinceEpic=2, sinceLegendary=2))
        self.assertEqual(original, dict(sinceEpic=0, sinceLegendary=0))
        self.assertTrue(45 <= items[0]['ilvl'] <= 57)
        self.assertTrue(all(i['stats'][s] > 0 for i in items[:1] for s in ('primary', 'armor')))

    def test_legendary_effects_prefer_unowned_and_seed_is_repeatable(self):
        owned = set()
        for n in range(10):
            item = game.generate_item('mage', 'mainhand', 'staff', 'legendary', 72,
                                       random.Random(n), owned_effects=owned)
            self.assertNotIn(item['effect']['id'], owned)
            owned.add(item['effect']['id'])
        again = game.generate_item('mage', 'mainhand', 'staff', 'legendary', 72,
                                    random.Random(10), owned_effects=owned)
        self.assertIn(again['effect']['id'], owned)
        args = ('mage', 5, {}, owned, dict(sinceEpic=4, sinceLegendary=23))
        self.assertEqual(game.roll_chest(*args, random.Random(14)),
                         game.roll_chest(*args, random.Random(14)))

    def test_curriculum_monte_carlo(self):
        self.assertEqual((len(LESSONS), len(COURSES)), (71, 13))
        # Welcome, then each path's lessons followed by the path chest.
        tiers = [1]
        for course in COURSES:
            tiers += [game.LESSON_TIERS[l['id']] for l in LESSONS
                      if l['course'] == course['id']]
            tiers.append(game.PATH_TIERS[course['id']])
        tiers += [min(5, 2 + (stage - 1) // 3) for stage in range(1, 11)]
        counts = Counter()
        levels = defaultdict(list)
        totals = []
        minimum_legendary = float('inf')
        half_lesson_legendary = 0
        for player in range(1000):
            rng = random.Random(player)
            cid = game.CLASSES[player % len(game.CLASSES)]['id']
            equipment = {i['slot']: i for i in game.starter_kit(cid, rng, STAMP)}
            luck = dict(sinceEpic=0, sinceLegendary=0)
            owned_effects = set()
            per_player = Counter()
            for tier in tiers:
                items, luck = game.roll_chest(cid, tier, equipment, owned_effects, luck, rng)
                for item in items:
                    per_player[item['rarity']] += 1
                    levels[tier].append(item['ilvl'])
                    if item['effect']:
                        owned_effects.add(item['effect']['id'])
            minimum_legendary = min(minimum_legendary, per_player['legendary'])
            totals.append(sum(per_player.values()))
            counts.update(per_player)
            half_rng = random.Random(player + 10000)
            half_luck = dict(sinceEpic=0, sinceLegendary=0)
            for lesson in LESSONS[:len(LESSONS) // 2]:
                items, half_luck = game.roll_chest(cid, game.LESSON_TIERS[lesson['id']],
                                                  equipment, set(), half_luck, half_rng)
                half_lesson_legendary += sum(i['rarity'] == 'legendary' for i in items)
        means = {key: value / 1000 for key, value in counts.items()}
        low = sum(levels[1]) / len(levels[1])
        high = sum(levels[5]) / len(levels[5])
        self.assertTrue(2.0 <= means['legendary'] <= 5.5, means)
        self.assertTrue(10 <= means['epic'] <= 22, means)
        self.assertGreaterEqual(minimum_legendary, 1)
        self.assertGreaterEqual(high - low, 35)
        # Python from zero added 13 small chests and a path chest: about 17 items.
        self.assertTrue(125 <= sum(totals) / 1000 <= 165)
        self.assertTrue(40 <= means['rare'] <= 65, means)
        self.assertTrue(.2 <= half_lesson_legendary / 1000 <= 1.2)
        print('\nHero Monte Carlo (1000 fixed-seed players): ' + json.dumps(dict(
            means=means, items=sum(totals) / 1000, minLegendary=minimum_legendary,
            tier1Ilvl=round(low, 3), tier5Ilvl=round(high, 3),
            halfLessonsLegendary=half_lesson_legendary / 1000)), flush=True)


class GameStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ml-game-unit-')
        self.db = sqlite3.connect(Path(self.tmp.name) / 'game.sqlite3')
        self.db.execute('PRAGMA foreign_keys=ON')
        game.ensure_schema(self.db)
        self.progress = progress_fixture()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def action(self, action, body, rng=None):
        return game.handle(self.db, action, body, self.progress, rng or random.Random(55))

    def hero(self, cid='warrior'):
        return self.action('hero', dict(name='  Durgan  ', race='orc', **{'class': cid}))['game']

    def add_item(self, cid, slot, base):
        with self.db:
            return game.store_item(self.db, game.generate_item(
                cid, slot, base, 'rare', 35, random.Random(1), 'fixture', STAMP))

    def test_chest_derivation_and_tiers(self):
        for course in COURSES:
            lessons = [l for l in LESSONS if l['course'] == course['id']]
            base = game.COURSE_DIFFICULTY.get(course['id'], 2)
            self.assertEqual(game.PATH_TIERS[course['id']], min(5, base + 3))
            for index, lesson in enumerate(lessons):
                bonus = 2 if index == len(lessons) - 1 else 1 if index >= len(lessons) / 2 else 0
                self.assertEqual(game.LESSON_TIERS[lesson['id']], min(5, base + bonus))
        self.assertEqual(game.earned_chests(self.progress), [])
        self.progress['completed']['foundations-1'] = dict(at=STAMP, xp=100)
        sources = {c['source']: c for c in game.earned_chests(self.progress)}
        self.assertEqual(set(sources), {'lesson:foundations-1'})
        self.assertEqual(sources['lesson:foundations-1']['subtitle'], 'ML foundations')
        for lesson in [l for l in LESSONS if l['course'] == 'foundations']:
            self.progress['completed'][lesson['id']] = dict(at=STAMP, xp=lesson['xp'])
        later = '2026-10-06T01:00:00+00:00'
        self.progress['completed']['foundations-3']['at'] = later
        projects = [dict(id=d, title=d.title(), steps=['One', 'Two'], level=level)
                    for d, level in (('start', 'Start small'), ('build', 'Build next'),
                                     ('capstone', 'Capstone'), ('unknown', None))]
        projects += [dict(id='empty', title='Empty', steps=[])]
        self.progress['projects'] = projects
        self.progress['projectState'] = {p['id']: dict(reviewed=[0, 0], updatedAt=1000)
                                         for p in projects}
        self.progress['guides'] = [dict(id='guide-a', title='Guide', bookId='book-a', bookTitle='Book')]
        self.progress['readingState'] = {'wrong-book': dict(completed=['guide-a'], updatedAt=1000)}
        self.assertFalse(any(c['kind'] in ('project', 'reading')
                             for c in game.earned_chests(self.progress)))
        for saved in self.progress['projectState'].values():
            saved['reviewed'] = [1, 0]
        self.progress['readingState']['book-a'] = dict(completed=['guide-a'], updatedAt=2000)
        sources = {c['source']: c for c in game.earned_chests(self.progress)}
        self.assertEqual(sources['path:foundations']['earnedAt'], later)
        self.assertEqual(sources['path:foundations']['title'], 'ML foundations mastered')
        for project_id, tier in [('start', 2), ('build', 3), ('capstone', 4), ('unknown', 3)]:
            reward = sources['project:' + project_id]
            self.assertEqual(reward['tier'], tier)
            self.assertEqual(reward['subtitle'], 'Project walkthrough')
            self.assertEqual(reward['earnedAt'], '1970-01-01T00:00:01+00:00')
        self.assertNotIn('project:empty', sources)
        self.assertEqual(sources['reading:guide-a']['earnedAt'], '1970-01-01T00:00:02+00:00')
        self.assertEqual(sources['reading:guide-a']['subtitle'], 'Book')
        self.assertNotIn('welcome', sources)
        saved = self.hero()
        self.assertIn('welcome', [c['source'] for c in saved['chests']['unopened']])
        self.assertEqual((saved['hero']['xp'], saved['hero']['level'],
                          saved['hero']['levelProgress']), (650, 7, .5))
        dates = [datetime.fromisoformat(c['earnedAt']) for c in saved['chests']['unopened']]
        self.assertEqual(dates, sorted(dates))

    def test_project_chests_need_every_task_and_checks_add_a_tier(self):
        def task(tid, checked=True):
            verify = dict(commands=['run'], expect='ok')
            if checked:
                verify['check'] = dict(type='contains', value='ok')
            return dict(id=tid, title=tid.title(), verify=verify)
        projects = [dict(id=level.split()[0].lower(), title=level, level=level,
                         tasks=[task('one'), task('two'), task('read', checked=False)],
                         stretch=task('extra'), steps=['One', 'Two', 'Read'])
                    for level in ('Start small', 'Build next', 'Capstone')]
        self.progress['projects'] = projects
        state = self.progress['projectState'] = {
            p['id']: dict(reviewed=[0, 1], updatedAt=1000, tasks={}) for p in projects}

        def chests():
            return {c['source']: c for c in game.earned_chests(self.progress)
                    if c['kind'] == 'project'}
        # Ticking two of three tasks is not finished, even with every check and the stretch passed.
        state['capstone']['tasks'] = {t: dict(verifiedAt=5) for t in ('one', 'two', 'extra')}
        self.assertEqual(chests(), {})
        for saved in state.values():
            saved['reviewed'] = [0, 1, 2]
        self.assertEqual({s: c['tier'] for s, c in chests().items()},
                         {'project:start': 2, 'project:build': 3, 'project:capstone': 5})
        self.assertEqual(chests()['project:capstone']['subtitle'], 'Project · every check passed')
        self.assertEqual(chests()['project:start']['subtitle'], 'Project')
        # One missing check removes the bonus; the stretch task and unchecked tasks never count.
        state['start']['tasks'] = dict(one=dict(verifiedAt=5), two=dict(notes='later'))
        state['build']['tasks'] = dict(one=dict(verifiedAt=5), two=dict(verifiedAt=6))
        self.assertEqual({s: c['tier'] for s, c in chests().items()},
                         {'project:start': 2, 'project:build': 4, 'project:capstone': 5})
        # A project without any checks earns its level's tier only.
        projects[0]['tasks'] = [task('one', False), task('two', False), task('read', False)]
        self.assertEqual(chests()['project:start']['tier'], 2)

    def test_retired_projects_keep_earned_chests(self):
        self.progress['retiredProjects'] = [dict(id='public-micrograd', title='micrograd', steps=3),
                                            dict(id='public-pokerl', title='PokeRL', steps=3)]
        self.progress['projectState'] = {
            'public-micrograd': dict(notes='kept', reviewed=[0, 1, 2], updatedAt=1000),
            'public-pokerl': dict(notes='', reviewed=[0, 2], updatedAt=1000),
            'removed-local-project': dict(notes='x', reviewed=[0], updatedAt=1000)}
        chests = {c['source']: c for c in game.earned_chests(self.progress)}
        self.assertEqual(set(chests), {'project:public-micrograd'})
        self.assertEqual((chests['project:public-micrograd']['tier'],
                          chests['project:public-micrograd']['subtitle']), (3, 'Retired project'))
        self.hero()
        opened = self.action('open', dict(source='project:public-micrograd'))
        self.assertEqual(opened['chest']['source'], 'project:public-micrograd')

    def test_schema_is_idempotent_and_progress_cap(self):
        self.hero()
        game.ensure_schema(self.db)
        self.progress['completed'] = {'test': dict(at=STAMP, xp=10000)}
        saved = game.state(self.db, self.progress)
        self.assertEqual(saved['hero']['level'], 60)
        self.assertEqual(saved['hero']['levelProgress'], 1.)
        self.assertTrue(game.from_millis(2**53 - 1).startswith('9999-12-31'))

    def test_eligibility_can_revoke_unopened_but_not_opened_history(self):
        self.progress = full_progress()
        no_hero = game.state(self.db, self.progress)
        self.assertIsNone(no_hero['hero'])
        self.assertEqual(no_hero['items'], [])
        self.assertEqual(no_hero['equipment'], {})
        self.assertEqual(len(no_hero['chests']['unopened']), EARNED)
        with self.assertRaisesRegex(ValueError, 'Create a hero'):
            self.action('open', dict(source='lesson:foundations-1'))
        self.hero()
        opened = self.action('open', dict(source='lesson:foundations-1'))
        luck = opened['game']['luck']
        self.progress = progress_fixture()
        saved = game.state(self.db, self.progress)
        self.assertEqual([c['source'] for c in saved['chests']['unopened']], ['welcome'])
        self.assertEqual(saved['chests']['opened'][0]['source'], 'lesson:foundations-1')
        self.assertEqual(saved['luck'], luck)
        with self.assertRaisesRegex(ValueError, 'This chest is already open.'):
            self.action('open', dict(source='lesson:foundations-1'))
        self.progress = full_progress()
        self.assertNotIn('lesson:foundations-1', [c['source'] for c in
                                                game.state(self.db, self.progress)['chests']['unopened']])

    def test_equipment_swaps_ownership_and_wrong_class(self):
        saved = self.hero()
        original = saved['equipment']
        two_hand = self.add_item('warrior', 'mainhand', 'greatsword')
        saved = self.action('equip', dict(itemId=two_hand['id']))['game']
        self.assertNotIn('offhand', saved['equipment'])
        self.assertFalse(next(i for i in saved['items'] if i['id'] == original['mainhand'])['equipped'])
        self.assertFalse(next(i for i in saved['items'] if i['id'] == original['offhand'])['equipped'])
        saved = self.action('equip', dict(itemId=original['offhand']))['game']
        self.assertNotIn('mainhand', saved['equipment'])
        self.assertFalse(next(i for i in saved['items'] if i['id'] == two_hand['id'])['equipped'])
        saved = self.action('equip', dict(itemId=original['mainhand']))['game']
        self.assertEqual(saved['equipment']['offhand'], original['offhand'])
        other = self.add_item('mage', 'mainhand', 'wand')
        with self.assertRaisesRegex(ValueError, 'class cannot equip'):
            self.action('equip', dict(itemId=other['id']))
        with self.db:
            wrong = game.store_item(self.db, {**two_hand, 'slot': 'offhand'})
        with self.assertRaisesRegex(ValueError, 'class cannot equip'):
            self.action('equip', dict(itemId=wrong['id']))
        for value in (None, True, '1', -1, 999999, 2**63, 2**100):
            with self.assertRaises(ValueError):
                self.action('equip', dict(itemId=value))
        saved = self.action('unequip', dict(slot='chest'))['game']
        self.assertNotIn('chest', saved['equipment'])
        self.assertIn(original['chest'], [i['id'] for i in saved['items']])

    def test_failed_discard_and_failed_open_roll_back_everything(self):
        initial = self.hero()
        loose = self.add_item('warrior', 'mainhand', 'sword')
        before = game.export(self.db)
        for ids in ([loose['id'], initial['equipment']['chest']], [loose['id'], 999999]):
            with self.assertRaises(ValueError):
                self.action('discard', dict(itemIds=ids))
            self.assertEqual(game.export(self.db), before)
        # Fail after items and the chest have been inserted, before luck is saved.
        with patch.object(game, 'put_meta', side_effect=RuntimeError('injected write failure')):
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                self.action('open', dict(source='welcome'))
        self.assertEqual(game.export(self.db), before)
        self.action('discard', dict(itemIds=[loose['id']]))
        self.assertNotIn(loose['id'], [i['id'] for i in game.export(self.db)['items']])
        self.action('open', dict(source='welcome'))

    def test_backup_history_is_complete_and_retire_resets_all_game_tables(self):
        self.progress = full_progress()
        self.hero()
        sources = [c['source'] for c in game.state(self.db, self.progress)['chests']['unopened']]
        for index, source in enumerate(sources):
            self.action('open', dict(source=source), random.Random(index))
        saved = game.state(self.db, self.progress)
        exported = game.export(self.db)
        self.assertEqual(len(saved['chests']['opened']), 40)
        self.assertEqual(len(exported['chests']), EARNED + 1)
        self.assertEqual(len(exported['items']), len(saved['items']))
        self.assertEqual(exported['meta']['sinceEpic'], saved['luck']['sinceEpic'])
        self.assertEqual(exported['meta']['sinceLegendary'], saved['luck']['sinceLegendary'])
        battle = self.action('battle/start', {})['battle']
        self.action('battle/finish', dict(battleId=battle['id'], outcome='defeat',
                                          bossDamage=1200, kills=4, seconds=95))
        before = game.export(self.db)
        with self.assertRaises(ValueError):
            self.action('retire', dict(confirm='retire'))
        self.assertEqual(game.export(self.db), before)
        saved = self.action('retire', dict(confirm='RETIRE'))['game']
        self.assertIsNone(saved['hero'])
        self.assertEqual(saved['items'], [])
        self.assertEqual(saved['equipment'], {})
        self.assertEqual(saved['chests']['opened'], [])
        self.assertEqual(len(saved['chests']['unopened']), EARNED)
        self.assertEqual(saved['luck'], dict(sinceEpic=0, sinceLegendary=0))
        self.assertEqual(saved['battles'], dict(earned=EARNED, used=0, available=EARNED))
        self.assertEqual(saved['campaign']['stage'], 1)
        self.assertEqual(saved['campaign']['bossDamage'], 0)
        self.assertEqual(saved['lifetime'], dict(fights=0, victories=0, kills=0,
                                               deaths=0, totalDamage=0, bestDamage=0))
        for table in ('game_hero', 'game_items', 'game_equipment', 'game_chests', 'game_meta',
                      'game_battles'):
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0], 0)
        self.hero('mage')
        self.action('open', dict(source='lesson:foundations-1'))

    def test_state_persists_after_reconnect(self):
        self.hero()
        self.action('open', dict(source='welcome'))
        self.action('settings', dict(enabled=False))
        battle = self.action('battle/start', {})['battle']
        self.action('battle/finish', dict(battleId=battle['id'], outcome='defeat',
                                          bossDamage=750, kills=9, seconds=180))
        before = game.state(self.db, self.progress)
        self.db.close()
        self.db = sqlite3.connect(Path(self.tmp.name) / 'game.sqlite3')
        game.ensure_schema(self.db)
        self.assertEqual(game.state(self.db, self.progress), before)

    def test_campaign_damage_persists_and_boss_chest_never_grants_a_charge(self):
        with self.assertRaisesRegex(ValueError, 'Finish a lesson'):
            self.action('battle/start', {})
        self.hero()
        for index, damage in enumerate((700, 500, 300)):
            if index:
                self.progress['completed'][f'foundations-{index}'] = dict(at=STAMP, xp=100)
            battle = self.action('battle/start', {})['battle']
            self.assertEqual(battle['bossHp'], 3000)
            self.assertEqual(battle['bossRemaining'], 3000 - (0, 700, 1200)[index])
            response = self.action('battle/finish', dict(
                battleId=battle['id'], outcome='defeat', bossDamage=damage, kills=2, seconds=60))
            self.assertFalse(response['result']['stageCleared'])
            self.assertIsNone(response['result']['chest'])
            self.assertEqual(response['game']['campaign']['stage'], 1)
        self.progress['completed']['foundations-3'] = dict(at=STAMP, xp=100)
        response = self.action('battle/start', {})
        battle = response['battle']
        self.assertEqual(battle['bossDamage'], 1500)
        self.assertEqual(response['game']['battles'], dict(earned=4, used=4, available=0))
        # Running out of charges must leave this fight active and finishable.
        with self.assertRaisesRegex(ValueError, 'Finish a lesson'):
            self.action('battle/start', {})
        payload = dict(battleId=battle['id'], outcome='retreat', bossDamage=2**53 - 1,
                       kills=8, seconds=45)
        finished = self.action('battle/finish', payload)
        result, saved = finished['result'], finished['game']
        self.assertEqual({k: v for k, v in result.items() if k != 'chest'},
                         dict(outcome='victory', damage=1500, stageCleared=True, stage=2))
        reward = result['chest']
        self.assertEqual(reward['source'], 'boss:1')
        self.assertEqual(reward['kind'], 'boss')
        self.assertEqual(reward['tier'], 2)
        self.assertEqual(reward['title'], 'Grimpelt the Alpha defeated')
        self.assertEqual(reward['subtitle'], 'Stage 1 · Blighted Outskirts')
        self.assertEqual(saved['campaign']['bossDamage'], 0)
        self.assertEqual(saved['campaign']['bossRemaining'], 5100)
        self.assertEqual(saved['campaign']['stagesCleared'], 1)
        self.assertEqual(saved['lifetime'], dict(fights=4, victories=1, kills=14, deaths=3,
                                               totalDamage=3000, bestDamage=1500))
        self.assertEqual(saved['battles'], dict(earned=4, used=4, available=0))
        self.assertEqual(reward['earnedAt'], saved['history'][0]['finishedAt'])
        before = game.export(self.db)
        with self.assertRaisesRegex(ValueError, 'battle has ended'):
            self.action('battle/finish', payload)
        self.assertEqual(game.export(self.db), before)
        self.action('open', dict(source='boss:1'))
        self.assertEqual(game.summary(self.db, self.progress)['battles'], 0)
        with self.assertRaisesRegex(ValueError, 'already open'):
            self.action('open', dict(source='boss:1'))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM game_battles WHERE outcome='victory'").fetchone()[0], 1)

    def test_settings_summary_disabled_rewards_and_retirement(self):
        self.assertEqual(game.summary(self.db, self.progress),
                         dict(enabled=True, hero=False, unopened=0, battles=0, stage=1))
        self.action('settings', dict(enabled=False))
        self.progress = full_progress()
        self.assertEqual(game.summary(self.db, self.progress),
                         dict(enabled=False, hero=False, unopened=EARNED, battles=EARNED, stage=1))
        saved = self.hero()
        self.assertFalse(saved['enabled'])
        self.assertEqual(saved['battles'], dict(earned=EARNED + 1, used=0, available=EARNED + 1))
        battle = self.action('battle/start', {})['battle']
        self.action('battle/finish', dict(battleId=battle['id'], outcome='victory',
                                          bossDamage=3000, kills=1, seconds=30))
        self.action('open', dict(source='welcome'))
        before = game.export(self.db)
        statements = []
        self.db.set_trace_callback(statements.append)
        with patch.object(game, 'inventory', side_effect=AssertionError('inventory read')), \
             patch.object(game, 'export', side_effect=AssertionError('full export')), \
             patch.object(game, 'state', side_effect=AssertionError('full state')):
            summary = game.summary(self.db, self.progress)
        self.db.set_trace_callback(None)
        self.assertEqual(summary, dict(enabled=False, hero=True, unopened=EARNED + 1, battles=EARNED, stage=2))
        self.assertEqual(game.export(self.db), before)
        self.assertTrue(all(q.startswith(('SELECT', 'BEGIN', 'COMMIT')) for q in statements), statements)
        self.assertFalse(any('game_items' in q or 'SELECT data FROM game_chests' in q for q in statements))
        saved = self.action('settings', dict(enabled=True))['game']
        self.assertEqual(len(saved['chests']['unopened']), EARNED + 1)
        self.assertEqual(saved['battles']['available'], EARNED)
        self.action('settings', dict(enabled=False))
        retired = self.action('retire', dict(confirm='RETIRE'))['game']
        self.assertFalse(retired['enabled'])
        self.assertEqual(retired['campaign']['stage'], 1)
        self.assertEqual(retired['campaign']['bossDamage'], 0)
        self.assertEqual(retired['history'], [])
        self.assertEqual(retired['battles'], dict(earned=EARNED, used=0, available=EARNED))
        self.assertFalse(any(c['kind'] == 'boss' for c in retired['chests']['unopened']))
        self.assertEqual(game.export(self.db)['battles'], [])
        self.assertFalse(self.hero('mage')['enabled'])
        # Progress can be revoked; spent charges are never refunded by opening loot.
        self.action('battle/start', {})
        self.action('battle/start', {})
        self.progress = progress_fixture()
        self.assertEqual(game.state(self.db, self.progress)['battles'],
                         dict(earned=1, used=2, available=0))

    def test_abandoned_history_and_complete_battle_backup(self):
        self.progress = full_progress()
        self.hero()
        first = self.action('battle/start', {})['battle']
        second = self.action('battle/start', {})['battle']
        saved = game.state(self.db, self.progress)
        self.assertEqual(saved['history'][0]['id'], first['id'])
        self.assertEqual(saved['history'][0]['outcome'], 'abandoned')
        self.assertEqual(saved['history'][0]['damage'], 0)
        self.assertTrue(saved['history'][0]['finishedAt'])
        self.assertEqual(saved['lifetime']['fights'], 2)
        self.assertEqual(saved['lifetime']['deaths'], 0)
        with self.assertRaisesRegex(ValueError, 'battle has ended'):
            self.action('battle/finish', dict(battleId=first['id'], outcome='victory',
                                              bossDamage=3000, kills=1, seconds=5))
        self.action('battle/finish', dict(battleId=second['id'], outcome='victory',
                                          bossDamage=10, kills=3, seconds=20))
        self.assertEqual(game.state(self.db, self.progress)['history'][0]['outcome'], 'defeat')
        for _ in range(14):
            battle = self.action('battle/start', {})['battle']
            self.action('battle/finish', dict(battleId=battle['id'], outcome='retreat',
                                              bossDamage=10, kills=1, seconds=20))
        active = self.action('battle/start', {})['battle']
        saved = game.state(self.db, self.progress)
        self.assertEqual(len(saved['history']), 12)
        self.assertEqual([h['id'] for h in saved['history']], list(range(active['id'] - 1,
                                                                      active['id'] - 13, -1)))
        self.assertEqual(saved['lifetime'], dict(fights=17, victories=0, deaths=1, kills=17,
                                               totalDamage=150, bestDamage=10))
        exported = game.export(self.db)
        self.assertEqual(len(exported['battles']), 17)
        self.assertEqual(exported['battles'][0]['outcome'], 'active')
        self.assertEqual(set(exported['battles'][0]), set(game.BATTLE_COLUMNS))

    def test_campaign_enters_abyss_and_chest_tiers_follow_slain_stage(self):
        self.progress = full_progress()
        self.hero()
        for stage in range(1, 17):
            response = self.action('battle/start', {})
            battle = response['battle']
            self.assertEqual(battle['stage'], stage)
            finished = self.action('battle/finish', dict(
                battleId=battle['id'], outcome='defeat', bossDamage=battle['bossHp'],
                kills=1, seconds=1))
            reward = finished['result']['chest']
            self.assertEqual(reward['source'], f'boss:{stage}')
            self.assertEqual(reward['tier'], min(5, 2 + (stage - 1) // 3))
            self.assertIn(reward, finished['game']['chests']['unopened'])
        saved = game.state(self.db, self.progress)
        self.assertEqual(saved['campaign']['stageName'], 'The Abyss · Depth 7')
        self.assertEqual(saved['campaign']['bossName'], 'Abyssal Behemoth')
        self.assertEqual(saved['campaign']['stagesCleared'], 16)
        self.assertEqual(saved['battles'], dict(earned=EARNED + 1, used=16, available=EARNED + 1 - 16))
        self.assertEqual(game.summary(self.db, self.progress)['unopened'], EARNED + 1 + 16)

    def test_battle_failures_roll_back_and_wrong_stage_is_rejected(self):
        self.progress = full_progress()
        self.hero()
        battle = self.action('battle/start', {})['battle']
        before = game.export(self.db)
        with patch.object(game, 'state', side_effect=RuntimeError('response failed')):
            with self.assertRaisesRegex(RuntimeError, 'response failed'):
                self.action('battle/start', {})
        self.assertEqual(game.export(self.db), before)
        payload = dict(battleId=battle['id'], outcome='victory', bossDamage=3000, kills=1, seconds=2)
        original_put = game.put_meta
        def fail_second_write(db, key, value):
            if key == 'bossDamage':
                raise RuntimeError('damage write failed')
            original_put(db, key, value)
        with patch.object(game, 'put_meta', side_effect=fail_second_write):
            with self.assertRaisesRegex(RuntimeError, 'damage write failed'):
                self.action('battle/finish', payload)
        self.assertEqual(game.export(self.db), before)
        with self.db:
            self.db.execute('UPDATE game_battles SET stage=2 WHERE id=?', (battle['id'],))
        with self.assertRaisesRegex(ValueError, 'stage'):
            self.action('battle/finish', payload)
        with self.db:
            self.db.execute('UPDATE game_battles SET stage=1 WHERE id=?', (battle['id'],))
        self.assertEqual(self.action('battle/finish', payload)['result']['stage'], 2)

    def test_revision_one_upgrade_preserves_loot_and_removes_records(self):
        self.hero()
        self.action('open', dict(source='welcome'))
        before = game.export(self.db)
        with self.db:
            game.put_meta(self.db, 'records', {'legacy': 'fixture'})
        with self.db:
            game.ensure_schema(self.db)
        with self.db:
            game.ensure_schema(self.db)
        self.assertIsNone(self.db.execute("SELECT 1 FROM game_meta WHERE key='records'").fetchone())
        self.assertEqual(game.export(self.db), before)
        saved = game.state(self.db, self.progress)
        self.assertNotIn('records', saved)
        self.assertTrue(saved['enabled'])
        self.assertEqual(saved['battles']['available'], 1)


class GameApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='ml-game-api-', ignore_cleanup_errors=True)
        cls.addClassCleanup(cls.tmp.cleanup)
        directory = Path(cls.tmp.name)
        project = dict(id='sample', title='Sample project', summary='Synthetic fixture',
                       tracks=['backend'], steps=['Trace request', 'Test retry'])
        (directory / 'portfolio.json').write_text(json.dumps(dict(version=1, projects=[project])))
        import_book(make_epub(directory / 'fixture.epub'), directory, 'gpu-glossary')
        # Give the synthetic two-chapter fixture one real guide locator, without real book data.
        manifest = directory / 'library' / 'gpu-glossary' / 'book.json'
        data = json.loads(manifest.read_text())
        data['toc'][0]['key'] = 'device-software--kernel'
        manifest.write_text(json.dumps(data))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        if cls.port == 7318:
            raise RuntimeError('Refusing the production port')
        cls.url = f'http://127.0.0.1:{cls.port}'
        cls.proc = subprocess.Popen(
            [sys.executable, str(ROOT / 'backend/server.py'), '--port', str(cls.port)],
            env={**os.environ, 'ML_WORKSHOP_DATA_DIR': cls.tmp.name, 'PYTHONDONTWRITEBYTECODE': '1'},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(cls.stop_server)
        cls.token = server_token(cls.url, directory, cls.proc)

    @classmethod
    def stop_server(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
            cls.proc.wait()

    def request(self, path, body=None, headers=None):
        headers = {'Content-Type': 'application/json', 'X-Workshop-Token': self.token,
                   **(headers or {})}
        headers = {key: value for key, value in headers.items() if value is not None}
        request = urllib.request.Request(self.url + path,
                                         data=json.dumps(body).encode() if body is not None else None,
                                         headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def assert_error(self, path, body, status=400, headers=None):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request(path, body, headers)
        self.assertEqual(caught.exception.code, status)
        with caught.exception as response:
            data = json.load(response)
        self.assertIsInstance(data['error'], str)
        return data['error']

    def setUp(self):
        self.request('/api/game/retire', dict(confirm='RETIRE'))
        self.request('/api/game/settings', dict(enabled=True))
        # Close explicitly: `with connect()` only commits, and Windows cannot delete an open database.
        db = sqlite3.connect(Path(self.tmp.name) / 'workshop.sqlite3')
        try:
            with db:
                for table in ('completions', 'project_state', 'reading_state'):
                    db.execute('DELETE FROM ' + table)
        finally:
            db.close()

    def hero(self, **patches):
        body = dict(name='Durgan', race='orc', **{'class': 'warrior'})
        return self.request('/api/game/hero', {**body, **patches})['game']

    def test_http_lifecycle_and_backup(self):
        initial = self.request('/api/game')
        self.assertIsNone(initial['hero'])
        self.assertEqual(initial['chests'], dict(opened=[], unopened=[]))
        self.assertEqual(set(initial), {'hero', 'items', 'equipment', 'chests',
                                       'luck', 'enabled', 'battles', 'campaign',
                                       'lifetime', 'history', 'catalog'})
        self.assertEqual((len(initial['catalog']['races']), len(initial['catalog']['classes'])), (13, 12))
        saved = self.hero(name='  Durgan  ')
        self.assertEqual(saved['hero']['name'], 'Durgan')
        self.assertEqual(len(saved['items']), 5)
        self.assertTrue(all(i['equipped'] for i in saved['items']))
        self.assertEqual(set(saved['equipment']), {'chest', 'legs', 'feet', 'mainhand', 'offhand'})
        self.assertEqual(saved['chests']['unopened'][0]['source'], 'welcome')
        opened = self.request('/api/game/open', dict(source='welcome'))
        self.assertEqual(len(opened['items']), 1)
        item = opened['items'][0]
        self.assertEqual(set(item), {'id', 'slot', 'base', 'rarity', 'ilvl', 'name', 'primaryStat',
                                     'twoHand', 'stats', 'effect', 'flavor', 'seed', 'source',
                                     'obtainedAt', 'equipped'})
        self.assertFalse(item['equipped'])
        self.assertEqual(opened['chest']['itemIds'], [item['id']])
        self.assertEqual(self.assert_error('/api/game/open', dict(source='welcome')),
                         'This chest is already open.')
        equipped = self.request('/api/game/equip', dict(itemId=item['id']))['game']
        self.assertEqual(equipped['equipment'][item['slot']], item['id'])
        self.assert_error('/api/game/discard', dict(itemIds=[item['id']]))
        self.request('/api/game/unequip', dict(slot=item['slot']))
        saved = self.request('/api/game/discard', dict(itemIds=[item['id']]))['game']
        self.assertNotIn(item['id'], [i['id'] for i in saved['items']])
        backup = self.request(self.request('/api/backup', {})['url'])
        self.assertEqual(set(backup['game']), {'hero', 'items', 'equipment', 'chests', 'meta', 'battles'})
        self.assertEqual(backup['game']['items'], saved['items'])
        self.assertEqual(backup['game']['equipment'], saved['equipment'])
        self.assertEqual(backup['game']['meta']['enabled'], saved['enabled'])
        self.assertEqual(backup['game']['battles'], [])
        self.assertEqual(backup['game']['chests'], saved['chests']['opened'])
        retired = self.request('/api/game/retire', dict(confirm='RETIRE'))['game']
        self.assertIsNone(retired['hero'])
        self.assertEqual(retired['items'], [])
        self.assertEqual(retired['chests'], dict(opened=[], unopened=[]))
        self.assertEqual(retired['luck'], dict(sinceEpic=0, sinceLegendary=0))

    def test_progress_routes_earn_chests_without_a_hero(self):
        solution = self.request('/api/solution/foundations-1')['solution']
        result = self.request('/api/run', dict(lessonId='foundations-1', code=solution, mode='check'))
        self.assertTrue(result['passed'])
        self.request('/api/project/state', dict(projectId='sample', notes='', reviewed=[0, 1], updatedAt=2000))
        guides = self.request('/api/library')['guides']
        self.assertEqual(guides[0]['id'], 'gpu-threads')
        self.request('/api/library/state', dict(bookId='gpu-glossary', location=1, notes='',
                                               bookmarks=[], completed=['gpu-threads'], updatedAt=3000))
        saved = self.request('/api/game')
        self.assertIsNone(saved['hero'])
        sources = {c['source']: c for c in saved['chests']['unopened']}
        self.assertEqual(set(sources), {'lesson:foundations-1', 'project:sample', 'reading:gpu-threads'})
        self.assertEqual(sources['project:sample']['tier'], 3)
        self.assertEqual(sources['reading:gpu-threads']['tier'], 2)
        self.assert_error('/api/game/open', dict(source='lesson:foundations-1'))
        saved = self.hero()
        self.assertEqual(saved['hero']['xp'], 100)
        self.request('/api/game/open', dict(source='project:sample'))
        self.request('/api/game/open', dict(source='reading:gpu-threads'))
        self.request('/api/game/retire', dict(confirm='RETIRE'))
        self.assertIn('foundations-1', self.request('/api/state')['completed'])
        self.assertEqual(len(self.request('/api/game')['chests']['unopened']), 3)

    def test_campaign_http_start_abandon_finish_and_backup(self):
        self.assertEqual(self.assert_error('/api/game/battle/start', {}), game.NEXT_BATTLE)
        self.hero()
        solution = self.request('/api/solution/foundations-1')['solution']
        self.request('/api/run', dict(lessonId='foundations-1', code=solution, mode='check'))
        first = self.request('/api/game/battle/start', {})
        self.assertEqual(set(first['battle']), {'id', 'stage', 'stageName', 'bossName',
                                               'bossHp', 'bossDamage', 'bossRemaining'})
        self.assertEqual(first['game']['battles'], dict(earned=2, used=1, available=1))
        second = self.request('/api/game/battle/start', {})
        self.assertEqual(second['game']['history'][0]['outcome'], 'abandoned')
        self.assertEqual(second['game']['history'][0]['id'], first['battle']['id'])
        self.assertEqual(second['game']['battles'], dict(earned=2, used=2, available=0))
        payload = dict(battleId=first['battle']['id'], outcome='victory', bossDamage=1000,
                       kills=4, seconds=90)
        self.assert_error('/api/game/battle/finish', payload)
        response = self.request('/api/game/battle/finish', {**payload, 'battleId': second['battle']['id']})
        self.assertEqual(response['result'], dict(outcome='defeat', damage=1000,
                                                 stageCleared=False, stage=1, chest=None))
        self.assertEqual(response['game']['campaign']['bossRemaining'], 2000)
        self.assertEqual(self.assert_error('/api/game/battle/start', {}), game.NEXT_BATTLE)
        self.request('/api/project/state', dict(projectId='sample', notes='', reviewed=[0, 1], updatedAt=2000))
        third = self.request('/api/game/battle/start', {})['battle']
        self.assertEqual(third['bossDamage'], 1000)
        self.assertEqual(third['bossRemaining'], 2000)
        response = self.request('/api/game/battle/finish', {**payload, 'battleId': third['id'],
                                                           'bossDamage': 5000, 'outcome': 'defeat'})
        self.assertEqual(response['result']['outcome'], 'victory')
        self.assertEqual(response['result']['damage'], 2000)
        self.assertEqual(response['game']['campaign']['stage'], 2)
        self.assertEqual(response['game']['campaign']['bossDamage'], 0)
        self.assertEqual(response['game']['lifetime'], dict(fights=3, victories=1, kills=8,
                                                          deaths=1, totalDamage=3000, bestDamage=2000))
        self.assertEqual(response['game']['battles'], dict(earned=3, used=3, available=0))
        self.assertEqual(response['result']['chest']['source'], 'boss:1')
        backup = self.request(self.request('/api/backup', {})['url'])['game']
        self.assertEqual(len(backup['battles']), 3)
        self.assertEqual(backup['battles'][0]['outcome'], 'victory')
        self.assertEqual(backup['meta']['stage'], 2)
        self.assertEqual(backup['meta']['bossDamage'], 0)
        opened = self.request('/api/game/open', dict(source='boss:1'))
        self.assertEqual(opened['chest']['kind'], 'boss')
        self.assertEqual(opened['game']['battles']['available'], 0)
        self.assert_error('/api/game/battle/finish', {**payload, 'battleId': third['id']})
        self.assert_error('/api/game/open', dict(source='boss:1'))
        self.assert_error('/api/game/battle', {})

    def test_campaign_finish_payload_validation_and_bounds(self):
        self.hero()
        battle = self.request('/api/game/battle/start', {})['battle']
        payload = dict(battleId=battle['id'], outcome='defeat', bossDamage=10, kills=0, seconds=0)
        patches = [
            {'battleId': None}, {'battleId': 0}, {'battleId': -1}, {'battleId': True},
            {'battleId': str(battle['id'])}, {'battleId': 999999}, {'battleId': 2**63},
            {'outcome': 'abandoned'}, {'outcome': 'active'}, {'outcome': []}, {'outcome': None},
        ]
        for key, ceiling in (('bossDamage', 2**53 - 1), ('kills', 2000), ('seconds', 3600)):
            for value in (-1, ceiling + 1, 2**100, True, 1.5, '1', None, {}, [], float('nan')):
                patches.append({key: value})
        before = self.request('/api/game')
        for change in patches:
            with self.subTest(change=change):
                self.assert_error('/api/game/battle/finish', {**payload, **change})
        for key in payload:
            missing = {k: v for k, v in payload.items() if k != key}
            self.assert_error('/api/game/battle/finish', missing)
        self.assertEqual(self.request('/api/game'), before)
        finished = self.request('/api/game/battle/finish', {
            **payload, 'bossDamage': 0, 'kills': 2000, 'seconds': 3600, 'outcome': 'retreat'})
        self.assertEqual(finished['result']['damage'], 0)
        self.assertEqual(finished['result']['outcome'], 'retreat')
        self.assertEqual(finished['game']['lifetime']['kills'], 2000)
        self.assertEqual(finished['game']['lifetime']['deaths'], 0)
        self.assert_error('/api/game/battle/finish', payload)

    def test_settings_summary_and_guards(self):
        self.assertEqual(self.request('/api/game/summary'),
                         dict(enabled=True, hero=False, unopened=0, battles=0, stage=1))
        self.assert_error('/api/game/settings', dict(enabled=False), 403, {'X-Workshop-Token': None})
        self.assert_error('/api/game/settings', dict(enabled=False), 403, {'Origin': 'https://example.com'})
        self.assert_error('/api/game/summary', None, 403, {'Origin': 'https://example.com'})
        self.assert_error('/api/game/battle/start', {}, 403, {'X-Workshop-Token': None})
        self.assert_error('/api/game/battle/finish', {}, 403, {'X-Workshop-Token': None})
        for value in (None, 0, 1, 'false', [], {}):
            self.assert_error('/api/game/settings', dict(enabled=value))
        self.assert_error('/api/game/settings', {})
        response = self.request('/api/game/settings', dict(enabled=False))
        self.assertFalse(response['game']['enabled'])
        self.request('/api/project/state', dict(projectId='sample', notes='', reviewed=[0, 1], updatedAt=2000))
        self.assertEqual(self.request('/api/game/summary'),
                         dict(enabled=False, hero=False, unopened=1, battles=1, stage=1))
        self.hero()
        self.request('/api/game/settings', dict(enabled=True))
        self.assertEqual(self.request('/api/game/summary'),
                         dict(enabled=True, hero=True, unopened=2, battles=2, stage=1))
        self.request('/api/game/settings', dict(enabled=False))
        response = self.request('/api/game/retire', dict(confirm='RETIRE'))
        self.assertFalse(response['game']['enabled'])
        self.assertEqual(self.request('/api/game/summary'),
                         dict(enabled=False, hero=False, unopened=1, battles=1, stage=1))

    def test_concurrent_battles_use_one_charge_and_award_one_boss_chest(self):
        self.hero()
        def attempt(path, payload):
            try:
                return 200, self.request(path, payload)
            except urllib.error.HTTPError as error:
                with error:
                    return error.code, json.load(error)
        with ThreadPoolExecutor(max_workers=8) as pool:
            starts = list(pool.map(lambda _: attempt('/api/game/battle/start', {}), range(8)))
        self.assertEqual(Counter(status for status, _ in starts), {200: 1, 400: 7})
        self.assertTrue(all(body['error'] == game.NEXT_BATTLE for status, body in starts if status == 400))
        battle = next(body['battle'] for status, body in starts if status == 200)
        payload = dict(battleId=battle['id'], outcome='victory', bossDamage=3000, kills=1, seconds=20)
        with ThreadPoolExecutor(max_workers=8) as pool:
            finishes = list(pool.map(lambda _: attempt('/api/game/battle/finish', payload), range(8)))
        self.assertEqual(Counter(status for status, _ in finishes), {200: 1, 400: 7})
        saved = self.request('/api/game')
        self.assertEqual(saved['battles'], dict(earned=1, used=1, available=0))
        self.assertEqual(saved['campaign']['stage'], 2)
        self.assertEqual(saved['lifetime']['victories'], 1)
        self.assertEqual([c['source'] for c in saved['chests']['unopened'] if c['kind'] == 'boss'],
                         ['boss:1'])
        self.assertEqual(self.request('/api/game/summary'),
                         dict(enabled=True, hero=True, unopened=2, battles=0, stage=2))

    def test_concurrent_open_is_once_only(self):
        self.hero()
        before = self.request('/api/game')
        def attempt(_):
            try:
                return 200, self.request('/api/game/open', dict(source='welcome'))
            except urllib.error.HTTPError as error:
                with error:
                    return error.code, json.load(error)
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(attempt, range(8)))
        self.assertEqual(Counter(status for status, _ in responses), {200: 1, 400: 7})
        self.assertTrue(all(body['error'] == 'This chest is already open.'
                            for status, body in responses if status == 400))
        after = self.request('/api/game')
        self.assertEqual(len(after['items']), len(before['items']) + 1)
        self.assertEqual(len(after['chests']['opened']), 1)
        self.assertEqual(after['chests']['unopened'], [])

    def test_game_routes_keep_request_guards(self):
        body = dict(name='Durgan', race='orc', **{'class': 'warrior'})
        for headers in ({'X-Workshop-Token': None}, {'X-Workshop-Token': 'wrong'},
                        {'Origin': 'https://example.com'}, {'Sec-Fetch-Site': 'cross-site'},
                        {'Host': 'attacker.example'}):
            self.assert_error('/api/game/hero', body, 403, headers)
        self.assert_error('/api/game/hero', body, 415, {'Content-Type': 'text/plain'})
        self.assert_error('/api/game/hero', {'name': 'x' * 128001}, 413)
        self.assert_error('/api/game/hero', ['not', 'an', 'object'])
        self.assertIsNone(self.request('/api/game')['hero'])
        self.assert_error('/api/game', None, 403, {'Origin': 'https://example.com'})

    def test_invalid_names_and_action_payloads(self):
        for name in ('', 'A', '123', 'A  B', '-Durgan', "Durgan'", 'A_B', 'éowyn',
                     'A' * 17, 'A\nB', 'A\tB', None, 3, [], {}):
            self.assert_error('/api/game/hero', dict(name=name, race='orc', **{'class': 'warrior'}))
        for patch_body in ({'race': 'bad'}, {'race': []}, {'class': 'bad'}, {'class': {}}):
            self.assert_error('/api/game/hero', {**dict(name='Durgan', race='orc',
                                                      **{'class': 'warrior'}), **patch_body})
        self.assertIsNone(self.request('/api/game')['hero'])
        self.hero(name="O'Neil-Sun")
        self.assert_error('/api/game/hero', dict(name='Other', race='human', **{'class': 'mage'}))
        invalid = [
            ('open', {}), ('open', {'source': []}), ('open', {'source': 'path:cuda'}),
            ('equip', {}), ('equip', {'itemId': True}), ('equip', {'itemId': 999999}),
            ('equip', {'itemId': 2**63}), ('equip', {'itemId': 2**100}),
            ('unequip', {'slot': 'waist'}), ('unequip', {'slot': []}),
            ('discard', {'itemIds': []}), ('discard', {'itemIds': [True]}),
            ('discard', {'itemIds': [1] * 201}), ('discard', {'itemIds': [1.0]}),
            ('discard', {'itemIds': '1'}), ('discard', {'itemIds': [999999]}),
            ('discard', {'itemIds': [2**63]}), ('discard', {'itemIds': [2**100]}),
            ('retire', {}), ('retire', {'confirm': 'retire'}), ('unknown', {}),
        ]
        before = self.request('/api/game')
        for action, body in invalid:
            with self.subTest(action=action, body=body):
                self.assert_error('/api/game/' + action, body)
        self.assertEqual(self.request('/api/game'), before)


if __name__ == '__main__':
    unittest.main()
