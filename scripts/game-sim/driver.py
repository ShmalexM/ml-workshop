"""Balance reports for the hero game. Start it with `npm run game:sim`, which bundles the engine first.

Every fight runs the real battle engine (scripts/game-sim/fight.ts) in Node with simulated time.
The curriculum report drives the real backend/game.py on an in-memory database: it finishes
every lesson and project in order, opens each chest, equips upgrades and spends every battle.
The builds report allocates passive tree builds (backend/game_tree.py) and compares each one
with the same hero and gear without passives.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import queue
import random
import sqlite3
import statistics as S
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import game  # noqa: E402
import game_tree as tree  # noqa: E402
from courses import COURSES, LESSONS  # noqa: E402
from portfolio import load_portfolio  # noqa: E402

CLASSES = [c['id'] for c in game.CLASSES]
# Equal-gear profiles: (label, rarity, item level, hero level, stage).
PROFILES = [('A: starter gear, level 1, stage 1', 'starter', 5, 1, 1),
            ('B: Rare ilvl 40, level 20, stage 5', 'rare', 40, 20, 5),
            ('C: Epic ilvl 72, level 55, stage 10', 'epic', 72, 55, 10)]
UNCAPPED = 10**9


class Workers:
    """A pool of Node processes, each running one fight at a time."""
    def __init__(self, bundle, size):
        self.free = queue.Queue()
        self.all = [subprocess.Popen(['node', bundle], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True) for _ in range(size)]
        for proc in self.all:
            self.free.put(proc)

    @contextmanager
    def worker(self):
        proc = self.free.get()
        try:
            yield lambda req: self._fight(proc, req)
        finally:
            self.free.put(proc)

    def fight(self, req):
        with self.worker() as run:
            return run(req)

    @staticmethod
    def _fight(proc, req):
        proc.stdin.write(json.dumps(req) + '\n')
        proc.stdin.flush()
        out = json.loads(proc.stdout.readline())
        if 'error' in out:
            raise RuntimeError(out['error'])
        return out

    def close(self):
        for proc in self.all:
            proc.stdin.close()
            proc.wait()


def hero_numbers(gear, level):
    """Power and health as src/game/stats.ts computes them."""
    total = lambda key: sum(item['stats'].get(key, 0) for item in gear.values())
    main, off = gear.get('mainhand'), gear.get('offhand')
    weapon = (main['stats']['damage'] if main else 0) + (
        off['stats']['damage'] * .5 if off and off['stats']['damage'] > 0 else 0)
    return (round(14 + level * 1.6 + total('primary') + weapon * .55),
            round(320 + level * 16 + total('stamina') * 7))


def swap(gear, item):
    after = dict(gear)
    if item['slot'] == 'mainhand' and item['twoHand']:
        after.pop('offhand', None)
    if item['slot'] == 'offhand' and (gear.get('mainhand') or {}).get('twoHand'):
        after.pop('mainhand', None)
    after[item['slot']] = item
    return after


def gain(gear, item, level):
    """The relative Power plus Health change, like the armory's upgrade marker."""
    power, health = hero_numbers(gear, level)
    new_power, new_health = hero_numbers(swap(gear, item), level)
    return (new_power - power) / max(1, power) + (new_health - health) / max(1, health)


def profile_gear(cls, rarity, ilvl, seed=1):
    rng = random.Random(seed)
    if rarity == 'starter':
        return {item['slot']: item for item in game.starter_kit(cls, rng, '')}
    info, weapons, gear = game.CLASS_BY_ID[cls], game.STARTER_WEAPONS[cls], {}
    for slot in game.SLOTS:
        if slot == 'offhand':
            if not info['offhand'] or weapons[0] in game.TWO_HAND:
                continue
            base = weapons[1] if len(weapons) > 1 else info['offhand'][0]
        elif slot == 'mainhand':
            base = weapons[0]
        elif slot == 'back':
            base = 'cloak'
        else:
            base = info['armor']
        gear[slot] = game.generate_item(cls, slot, base, rarity, ilvl, rng)
    return gear


def battle_setup(battle):
    return {k: battle[k] for k in ('enemyHealth', 'enemyDamage') if k in battle}


def stage_request(cls, gear, level, stage, seed, auto=True, dodge=False, uncapped=True, passives=()):
    hp = game.boss_hp(stage)
    setup = battle_setup(game.campaign(dict(stage=stage, bossDamage=0)))
    return dict(cls=cls, gear=gear, level=level, stage=stage, bossHp=hp,
                bossRemaining=UNCAPPED if uncapped else hp, seed=seed, auto=auto, dodge=dodge,
                setup=setup, passives=[dict(mods=tree.NODES[nid]['mods']) for nid in passives])


def mean(values):
    values = list(values)
    return S.mean(values) if values else 0


def class_table(pool, seeds, profiles=PROFILES, auto=True):
    """Boss damage per fight at equal gear, with a boss that cannot die, so nothing is capped."""
    results = {}
    for label, rarity, ilvl, level, stage in profiles:
        jobs = [(cls, s) for cls in CLASSES for s in range(seeds)]
        out = list(pool_map(pool, lambda job: pool.fight(stage_request(
            job[0], profile_gear(job[0], rarity, ilvl), level, stage, 1000 + job[1], auto=auto)), jobs))
        rows = {}
        for (cls, _), res in zip(jobs, out):
            rows.setdefault(cls, []).append(res)
        results[label] = {cls: dict(damage=mean(r['bossDamage'] for r in rs),
                                    alive=S.median(r['deathT'] if r['deathT'] >= 0 else r['seconds'] for r in rs),
                                    stunned=mean(r['stunnedShare'] for r in rs),
                                    dps=mean(r['bossDps'] for r in rs),
                                    burns=max(r['maxBurnsPerSource'] for r in rs),
                                    afterDeath=max(r['damageAfterDeath'] for r in rs),
                                    power=rs[0]['stats']['power'], health=rs[0]['stats']['maxHp'],
                                    share=mean(r['bossDamage'] for r in rs) / game.boss_hp(stage))
                         for cls, rs in rows.items()}
    return results


def pool_map(pool, fn, items):
    with ThreadPoolExecutor(len(pool.all)) as ex:
        return list(ex.map(fn, items))


# Equal gear near each stage's power target: (rarity, item level, hero level) for stages 1–10.
STAGE_GEAR = [('starter', 5, 1), ('common', 14, 3), ('common', 24, 6), ('rare', 30, 9), ('rare', 38, 13),
              ('rare', 46, 17), ('epic', 52, 21), ('epic', 58, 26), ('epic', 64, 31), ('epic', 70, 37)]


def stage_table(pool, seeds):
    """Each class at every stage with the same gear, as boss damage per fight relative to the stage median."""
    profiles = [(f'stage {i}', r, il, lv, i) for i, (r, il, lv) in enumerate(STAGE_GEAR, 1)]
    results = class_table(pool, seeds, profiles)
    rel = {cls: [] for cls in CLASSES}
    for rows in results.values():
        med = S.median(r['damage'] for r in rows.values())
        for cls, r in rows.items():
            rel[cls].append(r['damage'] / med)
    return results, rel


def print_stages(results, rel):
    print('\nBoss damage per fight against the stage median, at equal gear near each stage target')
    print(f"{'class':13s} " + ' '.join(f'{i:>5d}' for i in range(1, 11)) + '   mean')
    for cls in sorted(rel, key=lambda c: -S.mean(rel[c])):
        print(f'{cls:13s} ' + ' '.join(f'{v - 1:+5.0%}' for v in rel[cls]) + f'  {S.mean(rel[cls]) - 1:+5.0%}')
    print(f"{'power':13s} " + ' '.join(f"{S.median(r['power'] for r in rows.values()):5.0f}" for rows in results.values()))
    print(f"{'alive s':13s} " + ' '.join(f"{S.median(r['alive'] for r in rows.values()):5.0f}" for rows in results.values()))
    print(f"{'boss share':13s} " + ' '.join(f"{S.median(r['share'] for r in rows.values()):5.0%}" for rows in results.values()))


def geared_table(pool, seeds):
    """Win rate against a boss at full health: gear at the stage's target, and gear one stage ahead."""
    rows = []
    for stage in range(1, 11):
        for label, (rarity, ilvl, level) in (('par', STAGE_GEAR[stage - 1]), ('ahead', STAGE_GEAR[min(stage, 9)] if stage < 10 else ('epic', 78, 50))):
            jobs = [(cls, dodge, s) for cls in CLASSES for dodge in (False, True) for s in range(seeds)]
            out = pool_map(pool, lambda job: pool.fight(stage_request(
                job[0], profile_gear(job[0], rarity, ilvl), level, stage, 2000 + job[2], dodge=job[1], uncapped=False)), jobs)
            power = out[0]['stats']['power']
            wins = {d: mean(r['outcome'] == 'victory' for (c, dd, _), r in zip(jobs, out) if dd == d) for d in (False, True)}
            share = {d: mean(min(1, r['bossDamage'] / game.boss_hp(stage)) for (c, dd, _), r in zip(jobs, out) if dd == d) for d in (False, True)}
            rows.append(dict(stage=stage, gear=label, power=power, target=game.stage_target(stage)[0],
                             autoWin=wins[False], dodgeWin=wins[True], autoShare=share[False], dodgeShare=share[True]))
    return rows


def print_geared(rows):
    print('\nAgainst a boss at full health: wins and boss health taken per fight, Auto and Auto with dodging')
    print(f"{'stage':>5s} {'gear':6s} {'power':>5s} {'target':>6s} {'auto win':>8s} {'dodge win':>9s} {'auto share':>10s} {'dodge share':>11s}")
    for r in rows:
        print(f"{r['stage']:5d} {r['gear']:6s} {r['power']:5d} {r['target']:6d} {r['autoWin']:8.0%} {r['dodgeWin']:9.0%} {r['autoShare']:10.0%} {r['dodgeShare']:11.0%}")


def print_classes(results):
    for label, rows in results.items():
        med = S.median(r['damage'] for r in rows.values())
        spread = max(r['damage'] for r in rows.values()) / max(1, min(r['damage'] for r in rows.values()))
        print(f'\n{label}  (median {med:,.0f} boss damage per fight; highest/lowest {spread:.2f}x)')
        print(f"{'class':13s} {'damage':>9s} {'vs median':>9s} {'boss %':>7s} {'alive s':>7s} {'boss dps':>8s} {'stunned':>7s} {'burns':>5s} {'power':>5s} {'health':>6s}")
        for cls in sorted(rows, key=lambda c: -rows[c]['damage']):
            r = rows[cls]
            print(f"{cls:13s} {r['damage']:9,.0f} {r['damage'] / med - 1:+9.0%} {r['share']:7.1%} {r['alive']:7.1f} {r['dps']:8,.0f} {r['stunned']:7.0%} {r['burns']:5d} {r['power']:5d} {r['health']:6d}")


def auto_table(pool, seeds, profiles=PROFILES):
    """Auto against standing still (no input: the hero only attacks what comes in range)."""
    rows = []
    for label, rarity, ilvl, level, stage in profiles:
        jobs = [(cls, auto, s) for cls in CLASSES for auto in (True, False) for s in range(seeds)]
        out = pool_map(pool, lambda job: pool.fight(stage_request(
            job[0], profile_gear(job[0], rarity, ilvl), level, stage, 500 + job[2], auto=job[1])), jobs)
        by = {}
        for (cls, auto, _), res in zip(jobs, out):
            by.setdefault((cls, auto), []).append(res)
        for cls in CLASSES:
            a, idle = by[(cls, True)], by[(cls, False)]
            rows.append(dict(profile=label[:1], cls=cls,
                             auto=mean(r['bossDamage'] for r in a), idle=mean(r['bossDamage'] for r in idle),
                             autoAlive=mean(r['deathT'] if r['deathT'] >= 0 else r['seconds'] for r in a),
                             idleAlive=mean(r['deathT'] if r['deathT'] >= 0 else r['seconds'] for r in idle)))
    return rows


def print_auto(rows):
    print('\nAuto against standing still: mean boss damage per fight and seconds alive')
    print(f"{'':2s} {'class':13s} {'auto':>9s} {'still':>9s} {'auto/still':>10s} {'alive':>6s} {'still':>6s}")
    worse = 0
    for r in rows:
        ratio = r['auto'] / max(1, r['idle'])
        flag = '  <' if r['auto'] < r['idle'] * .97 else ''
        worse += bool(flag)
        print(f"{r['profile']:2s} {r['cls']:13s} {r['auto']:9,.0f} {r['idle']:9,.0f} {ratio:10.2f} {r['autoAlive']:6.1f} {r['idleAlive']:6.1f}{flag}")
    print(f'Auto worse than standing still: {worse} of {len(rows)}')
    return worse


# ---------- passive tree builds ----------
# Small node preferences when a build spends points that its targets leave over.
FILL = dict(
    damage=dict(might=3, technique=2.6, sharp=2.4, swift=2, reach=1.4, flow=1.4, kindling=1, vigor=1, grit=.9, renewal=.4),
    tank=dict(vigor=3, grit=3, renewal=1.5, might=1.2, technique=1, sharp=.8, swift=.8, flow=.8, reach=.6, kindling=.4),
)
BURNS = {'druid', 'priest', 'mage', 'warlock'}
KEYSTONE_IDS = [k[0] for k in tree.KEYSTONES]
# A build's worth is the Power and Health multiplier at which the same hero without passives deals
# the same boss damage per fight. Boss damage itself grows much faster than that, because a hero who
# lives longer also kills the waves sooner. Checks: the whole tree (FULL_POINTS) is worth roughly
# +25-40% (median build), and at the points a hero has on reaching each stage no build is clearly
# worth more than +35% (its estimate minus two standard errors), so none puts a hero much beyond the
# stage's Power and Health target. Single fights vary a lot, so use 16 or more seeds per build.
SCALES = (.8, .9, 1, 1.1, 1.2, 1.3, 1.45, 1.6, 1.8, 2, 2.3)
FULL_GAIN = (1.25, 1.40)
STAGE_GAIN_MAX = 1.35
TOLERANCE = .02
# Every point the curriculum gives: level 60 and every path mastered.
FULL_POINTS = game.passive_points(dict(completed={l['id']: dict(xp=l['xp']) for l in LESSONS}))


def sector_of(cls):
    return next(s['id'] for s in tree.SECTORS if cls in s['classes'])


def distance(cls, target):
    return len(tree.path_to(cls, {tree.START_BY_CLASS[cls]}, target))


def notables(cls, sector):
    return sorted((n['id'] for n in tree.NODES.values() if n['kind'] == 'notable' and n['sector'] == sector),
                  key=lambda nid: (distance(cls, nid), nid))


def plan_build(cls, points, targets=(), fill='damage'):
    """Path to each target in turn while points last, then take the best small nodes next to the build."""
    start = tree.START_BY_CLASS[cls]
    chosen = {start}
    for target in targets:
        path = tree.path_to(cls, chosen, target)
        if path is not None and len(path) <= points - (len(chosen) - 1):
            chosen.update(path)
    weights = dict(FILL[fill])
    if cls in BURNS:
        weights['kindling'] = 2.2
    blocked = tree.STARTS - {start}

    def score(nid):
        node = tree.NODES[nid]
        return {'small': weights.get(node.get('small'), 0), 'notable': 4, 'keystone': -100}.get(node['kind'], -100)
    while len(chosen) - 1 < points:
        frontier = {n for a in chosen for n in tree.ADJACENCY[a] if n not in chosen and n not in blocked}
        best = max(frontier, key=lambda nid: (score(nid), nid))
        if score(best) < 0:
            break
        chosen.add(best)
    return sorted(chosen)


def builds_for(cls):
    """Archetypes: own sector, a defensive spread, each keystone first, and two hybrids across a bridge."""
    sector = sector_of(cls)
    order = [s['id'] for s in tree.SECTORS]
    i = order.index(sector)
    own = notables(cls, sector)
    out = [('own', own, 'damage'), ('tank', own, 'tank')]
    out += [(kid, [kid] + own, 'damage') for kid in KEYSTONE_IDS]
    for label, other in (('hybrid-ccw', order[i - 1]), ('hybrid-cw', order[(i + 1) % 4])):
        out.append((label, own[:1] + notables(cls, other)[:3] + own[1:], 'damage'))
    return out


def planned_points(level):
    """Points on reaching `level` when lessons are finished in curriculum order."""
    xp, done = 0, set()
    for kind, obj in tasks():
        if kind != 'lesson':
            continue
        if min(60, 1 + xp // 100) >= level:
            break
        done.add(obj['id'])
        xp += obj['xp']
    paths = sum(1 for c in COURSES if all(l['id'] in done for l in LESSONS if l['course'] == c['id']))
    return level - 1 + paths


def build_points():
    """(label, stage, rarity, item level, hero level, points): every campaign stage, then the full tree."""
    rows = [(f'stage {i}', i, r, il, lv, planned_points(lv)) for i, (r, il, lv) in enumerate(STAGE_GEAR, 1)]
    return rows + [('full', 10, 'epic', 72, 60, FULL_POINTS)]


def fit_curve(curve, center=0., width=.3):
    """Weighted least squares fit of log boss damage as a quadratic in log scale near `center`.
    Fitting several scales at once smooths single fights; the weights keep the fit local, because
    the curve bends where heroes start to survive the whole fight."""
    rows = [(math.log(k), math.log(max(1, dmg)), math.exp(-((math.log(k) - center) / width) ** 2))
            for k, dmg in curve]
    m = [[sum(w * x ** (i + j) for x, _, w in rows) for j in range(3)] +
         [sum(w * y * x ** i for x, y, w in rows)] for i in range(3)]
    for i in range(3):
        pivot = max(range(i, 3), key=lambda r: abs(m[r][i]))
        m[i], m[pivot] = m[pivot], m[i]
        for r in range(3):
            if r != i:
                f = m[r][i] / m[i][i]
                m[r] = [a - f * b for a, b in zip(m[r], m[i])]
    return tuple(m[i][3] / m[i][i] for i in range(3))


def equivalent(curve, damage):
    """The scale at which the hero without passives deals `damage`, and the curve's log-log slope there.
    Refits around the estimate twice, starting from the plain fit."""
    target = math.log(max(1, damage))
    x, fit = 0., fit_curve(curve, 0., 10.)
    for width in (10., .3, .3):
        fit = fit_curve(curve, x, width)
        a, b, c = fit
        lo, hi = math.log(.5), math.log(4)
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if a + b * mid + c * mid * mid < target else (lo, mid)
        x = (lo + hi) / 2
    return math.exp(x), max(.5, fit[1] + 2 * fit[2] * x)


def build_table(pool, seeds, points=None, classes=None):
    """Each archetype build's worth, against the same hero and gear without passives at several scales."""
    results = []
    for label, stage, rarity, ilvl, level, pts in points or build_points():
        jobs = []
        for cls in classes or CLASSES:
            gear = profile_gear(cls, rarity, ilvl)
            for k in SCALES:
                for s in range(seeds):
                    req = stage_request(cls, gear, level, stage, 3000 + s)
                    jobs.append((cls, ('scale', k), [], {**req, 'scale': k}))
            for name, targets, fill in builds_for(cls):
                chosen = plan_build(cls, pts, targets, fill)
                for s in range(seeds):
                    jobs.append((cls, name, chosen, stage_request(cls, gear, level, stage, 3000 + s, passives=chosen)))
        out = pool_map(pool, lambda job: pool.fight(job[3]), jobs)
        damage, nodes = {}, {}
        for (cls, name, chosen, _), res in zip(jobs, out):
            damage.setdefault((cls, name), []).append(res['bossDamage'])
            nodes[(cls, name)] = chosen
        for cls in classes or CLASSES:
            curve = [(k, mean(damage[(cls, ('scale', k))])) for k in SCALES]
            base = mean(damage[(cls, ('scale', 1))])
            for name, *_ in builds_for(cls):
                fights = damage[(cls, name)]
                dmg = mean(fights)
                gain, slope = equivalent(curve, dmg)
                # Two standard errors of the mean boss damage, carried through the curve.
                spread = 2 * S.stdev(fights) / max(1, dmg) / math.sqrt(len(fights)) / slope
                results.append(dict(point=label, stage=stage, points=pts, cls=cls, build=name,
                                    gain=gain, low=gain * math.exp(-spread), high=gain * math.exp(spread),
                                    damage=dmg / max(1, base),
                                    keystones=[n for n in nodes[(cls, name)] if n in KEYSTONE_IDS],
                                    spent=len(nodes[(cls, name)]) - 1))
    return results


def print_builds(rows):
    print('\nPassive tree builds, worth as a Power and Health multiplier on the same hero without passives')
    print('(the multiplier at which that hero deals the same boss damage per fight; raw boss damage ratio in brackets)')
    print(f"{'at':9s} {'points':>6s} {'median':>7s} {'lowest':>7s} {'highest':>8s} {'boss dmg':>9s}  highest build (2 standard errors)")
    for point in dict.fromkeys(r['point'] for r in rows):
        rs = [r for r in rows if r['point'] == point]
        top = max(rs, key=lambda r: r['gain'])
        print(f"{point:9s} {rs[0]['points']:6d} {S.median(r['gain'] for r in rs):7.2f} {min(r['gain'] for r in rs):7.2f} "
              f"{top['gain']:8.2f} {'(' + format(S.median(r['damage'] for r in rs), '.1f') + 'x)':>9s}  "
              f"{top['cls']} {top['build']} ({top['low']:.2f}-{top['high']:.2f})")
    full = [r for r in rows if r['point'] == 'full']
    if full:
        names = list(dict.fromkeys(r['build'] for r in full))
        print(f'\nFull tree ({FULL_POINTS} points, epic ilvl 72, level 60, stage 10): gain per class and build')
        print(f"{'class':13s} " + ' '.join(f'{n[:9]:>9s}' for n in names))
        for cls in dict.fromkeys(r['cls'] for r in full):
            by = {r['build']: r['gain'] for r in full if r['cls'] == cls}
            print(f'{cls:13s} ' + ' '.join(f'{by[n]:9.2f}' for n in names))
        print(f"{'median':13s} " + ' '.join(f"{S.median(r['gain'] for r in full if r['build'] == n):9.2f}" for n in names))


def tree_failures(rows):
    failures = []
    full = [r['gain'] for r in rows if r['point'] == 'full']
    if full:
        median = S.median(full)
        if not FULL_GAIN[0] - TOLERANCE <= median <= FULL_GAIN[1] + TOLERANCE:
            failures.append(f'the full tree is worth {median - 1:+.0%} for the median build, outside '
                            f'{FULL_GAIN[0] - 1:+.0%} to {FULL_GAIN[1] - 1:+.0%}')
    for r in rows:
        if r['point'] != 'full' and r['low'] > STAGE_GAIN_MAX:
            failures.append(f"{r['cls']} {r['build']} at {r['point']} ({r['points']} points) is worth "
                            f"{r['gain'] - 1:+.0%} ({r['low'] - 1:+.0%} to {r['high'] - 1:+.0%})")
    return failures


# ---------- curriculum ----------
# A folder without portfolio.json, so the public catalog is used.
PROJECTS = load_portfolio(Path(__file__).parent)['projects']


def tasks():
    out = []
    for i, course in enumerate(COURSES):
        out += [('lesson', lesson) for lesson in LESSONS if lesson['course'] == course['id']]
        if i < len(PROJECTS):
            out.append(('project', PROJECTS[i]))
    return out


def equip_upgrades(db, progress, rng, level):
    state = game.state(db, progress)
    by_id = {item['id']: item for item in state['items']}
    gear = {slot: by_id[iid] for slot, iid in state['equipment'].items()}
    for item in sorted((i for i in state['items'] if not i['equipped']), key=lambda i: -i['ilvl']):
        current = [gear.get(item['slot'])] + ([gear.get('offhand')] if item['slot'] == 'mainhand' and item['twoHand'] else [])
        legendary = any(c and c.get('effect') for c in current)
        if gain(gear, item, level) > (.2 if legendary else 0):
            game.handle(db, 'equip', dict(itemId=item['id']), progress, rng)
            gear = swap(gear, item)


def curriculum_run(pool, cls, seed, keep_gear=False, build=None):
    rng = random.Random(seed)
    db = sqlite3.connect(':memory:', isolation_level=None)
    game.ensure_schema(db)
    t0 = datetime(2027, 1, 1, tzinfo=timezone.utc)
    progress = dict(completed={}, projects=PROJECTS, projectState={}, readingState={}, guides=[], revealed={})
    game.handle(db, 'hero', dict(name='Sim', race='human', **{'class': cls}), progress, rng)
    log = []

    def level():
        return game.state(db, progress)['hero']['level']

    def open_all():
        while True:
            st = game.state(db, progress)
            if not st['chests']['unopened']:
                return
            game.handle(db, 'open', dict(source=st['chests']['unopened'][0]['source']), progress, rng)
            equip_upgrades(db, progress, rng, st['hero']['level'])

    with pool.worker() as fight:
        def fight_all(task):
            while game.state(db, progress)['battles']['available'] > 0:
                battle = game.handle(db, 'battle/start', {}, progress, rng)['battle']
                st = game.state(db, progress)
                by_id = {item['id']: item for item in st['items']}
                gear = {slot: by_id[iid] for slot, iid in st['equipment'].items()}
                lvl = st['hero']['level']
                passives = [dict(mods=tree.NODES[nid]['mods']) for nid in st['passives']['allocated']]
                res = fight(dict(cls=cls, gear=gear, level=lvl, stage=battle['stage'], bossHp=battle['bossHp'],
                                 bossRemaining=battle['bossRemaining'], seed=(seed * 1000 + len(log)) * 7919 + battle['stage'],
                                 setup=battle_setup(battle), passives=passives))
                done = game.handle(db, 'battle/finish', dict(
                    battleId=battle['id'], outcome=res['outcome'], bossDamage=int(res['bossDamage']),
                    kills=min(2000, res['kills']), seconds=min(3600, res['seconds'])), progress, rng)
                power, health = hero_numbers(gear, lvl)
                log.append(dict(fight=len(log) + 1, task=task, stage=battle['stage'], level=lvl, power=power,
                                health=health, before=battle['bossRemaining'], bossHp=battle['bossHp'],
                                damage=res['bossDamage'], outcome=done['result']['outcome'],
                                alive=res['deathT'] if res['deathT'] >= 0 else res['seconds'],
                                gear=gear if keep_gear else None))
                open_all()

        open_all()
        fight_all(0)
        for i, (kind, obj) in enumerate(tasks(), 1):
            at = t0 + timedelta(hours=i)
            if kind == 'lesson':
                progress['completed'][obj['id']] = dict(at=at.isoformat(), xp=obj['xp'])
            else:
                progress['projectState'][obj['id']] = dict(
                    reviewed=list(range(len(obj['steps']))), notes='What the project does and how it is built.',
                    updatedAt=int(at.timestamp() * 1000))
            open_all()
            if build:
                points = game.state(db, progress)['passives']['points']['earned']
                targets = next((t, f) for name, t, f in builds_for(cls) if name == build)
                game.handle(db, 'passives', dict(allocated=plan_build(cls, points, *targets)), progress, rng)
            fight_all(i)
    return log


def curriculum(pool, runs, classes=None, build=None):
    jobs = [((classes or CLASSES)[i % len(classes or CLASSES)], 7 + i) for i in range(runs)]
    return pool_map(pool, lambda job: (job[0], curriculum_run(pool, *job, build=build)), jobs)


def print_curriculum(results):
    per_stage = {}
    never = 0
    for _, log in results:
        for stage in range(1, 11):
            fights = [f for f in log if f['stage'] == stage]
            cleared = any(f['outcome'] == 'victory' for f in fights)
            if fights and cleared:
                per_stage.setdefault(stage, []).append(len(fights))
            elif stage == 10:
                never += 1
    print('\nCurriculum runs: fights to clear each stage, median (min–max), and par power and health')
    print(f"{'stage':>5s} {'fights':>14s} {'runs':>5s} {'power':>6s} {'health':>6s} {'boss share':>10s} {'won from full':>13s}")
    for stage in range(1, 11):
        f = per_stage.get(stage, [])
        firsts = [next(x for x in log if x['stage'] == stage) for _, log in results if any(x['stage'] == stage for x in log)]
        fights = [x for _, log in results for x in log if x['stage'] == stage]
        share = S.median(x['damage'] / x['bossHp'] for x in fights) if fights else 0
        full = sum(1 for x in fights if x['before'] == x['bossHp'] and x['outcome'] == 'victory')
        span = f"{S.median(f):.1f} ({min(f)}–{max(f)})" if f else '—'
        print(f"{stage:5d} {span:>14s} {len(f):5d} {S.median(x['power'] for x in firsts) if firsts else 0:6.0f} "
              f"{S.median(x['health'] for x in firsts) if firsts else 0:6.0f} {share:10.1%} {full:13d}")
    logs = [log for _, log in results]
    total = sum(len(log) for log in logs)
    wins = sum(1 for log in logs for f in log if f['outcome'] == 'victory')
    deaths = sum(1 for log in logs for f in log if f['outcome'] != 'victory' and f['alive'] < 239)
    print(f"Runs that never clear stage 10: {never} of {len(logs)}. Fights per run: {total / len(logs):.0f}. "
          f"Wins {wins / total:.1%}. Fights that end in death: {deaths / total:.1%}.")
    for n in (1, 10, 20, 40, 80):
        p = [log[n - 1]['power'] for log in logs if len(log) >= n]
        s = [log[n - 1]['stage'] for log in logs if len(log) >= n]
        if p:
            print(f'  fight {n:2d}: power {S.median(p):.0f}, stage {S.median(s):.0f}')
    final = [log[-1]['stage'] for log in logs]
    print(f'Final stage: median {S.median(final):.0f} ({min(final)}–{max(final)})')


def check(pool):
    """Quick rule checks used by tests/test_game.py."""
    failures = []
    for cls in ('warlock', 'priest', 'druid'):
        gear = profile_gear(cls, 'epic', 72)
        for seed in range(2):
            r = pool.fight(stage_request(cls, gear, 55, 10, 900 + seed))
            if r['maxBurnsPerSource'] > 3:
                failures.append(f'{cls}: {r["maxBurnsPerSource"]} burns from one source')
            if r['stunnedShare'] > .25:
                failures.append(f'{cls}: boss stunned {r["stunnedShare"]:.0%} of the time')
    for seed in range(3):
        r = pool.fight(stage_request('warlock', profile_gear('warlock', 'starter', 5), 1, 4, 700 + seed))
        if r['deathT'] >= 0 and r['damageAfterDeath'] > 0:
            failures.append(f'warlock: {r["damageAfterDeath"]} boss damage after death')
    for cls in ('monk', 'demonhunter'):
        a = [pool.fight(stage_request(cls, profile_gear(cls, 'starter', 5), 1, 1, 300 + s)) for s in range(4)]
        idle = [pool.fight(stage_request(cls, profile_gear(cls, 'starter', 5), 1, 1, 300 + s, auto=False)) for s in range(4)]
        if mean(r['bossDamage'] for r in a) < mean(r['bossDamage'] for r in idle) * .97:
            failures.append(f'{cls}: Auto deals less boss damage than standing still')
    # Passive tree: two stages and the full tree, one class per sector.
    points = [p for p in build_points() if p[0] in ('stage 7', 'stage 10', 'full')]
    failures += tree_failures(build_table(pool, 16, points, ['warrior', 'monk', 'druid', 'priest']))
    print('\n'.join(failures) or 'ok')
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report', nargs='?', default='all', choices=['all', 'classes', 'stages', 'geared', 'auto', 'curriculum', 'builds', 'check'])
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--seeds', type=int, default=8)
    parser.add_argument('--runs', type=int, default=24)
    parser.add_argument('--workers', type=int, default=min(10, os.cpu_count() or 4))
    parser.add_argument('--classes', default='')
    parser.add_argument('--json', default='')
    parser.add_argument('--build', default='', help='curriculum: allocate this archetype as points come in, e.g. own')
    parser.add_argument('--at', default='', help='builds: only these points, e.g. "stage 10,full"')
    args = parser.parse_args()
    pool = Workers(args.bundle, args.workers)
    out = {}
    code = 0
    try:
        if args.report == 'check':
            code = check(pool)
        if args.report in ('all', 'classes'):
            out['classes'] = class_table(pool, args.seeds)
            print_classes(out['classes'])
        if args.report in ('all', 'stages'):
            results, rel = stage_table(pool, args.seeds)
            out['stages'] = dict(results=results, relative=rel)
            print_stages(results, rel)
        if args.report in ('all', 'geared'):
            out['geared'] = geared_table(pool, max(2, args.seeds // 4))
            print_geared(out['geared'])
        if args.report in ('all', 'auto'):
            out['auto'] = auto_table(pool, max(4, args.seeds // 2))
            print_auto(out['auto'])
        if args.report in ('all', 'builds'):
            at = [a.strip() for a in args.at.split(',') if a.strip()]
            out['builds'] = build_table(pool, max(16, args.seeds), [p for p in build_points() if not at or p[0] in at],
                                        [c for c in args.classes.split(',') if c] or None)
            print_builds(out['builds'])
            failures = tree_failures(out['builds'])
            print('\n'.join(failures) or 'Tree checks: ok')
        if args.report in ('all', 'curriculum'):
            results = curriculum(pool, args.runs, [c for c in args.classes.split(',') if c] or None, args.build or None)
            out['curriculum'] = [dict(cls=c, log=log) for c, log in results]
            print_curriculum(results)
    finally:
        pool.close()
    if args.json:
        Path(args.json).write_text(json.dumps(out, default=str))
    return code


if __name__ == '__main__':
    sys.exit(main())
