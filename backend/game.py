"""Local hero inventory and earned loot; no learning progress is written here."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import random
import re
import secrets

from courses import COURSES, LESSONS
import game_tree


RACES = [
    dict(id=rid, name=name, faction=faction)
    for rid, name, faction in [
        ('human', 'Human', 'alliance'), ('dwarf', 'Dwarf', 'alliance'),
        ('nightelf', 'Night Elf', 'alliance'), ('gnome', 'Gnome', 'alliance'),
        ('draenei', 'Draenei', 'alliance'), ('worgen', 'Worgen', 'alliance'),
        ('orc', 'Orc', 'horde'), ('undead', 'Undead', 'horde'),
        ('tauren', 'Tauren', 'horde'), ('troll', 'Troll', 'horde'),
        ('bloodelf', 'Blood Elf', 'horde'), ('goblin', 'Goblin', 'horde'),
        ('pandaren', 'Pandaren', 'neutral'),
    ]
]
# Class colors: close to the familiar ones, but our own values, and readable on the dark game panels
# (at least 4.5:1 contrast).
CLASSES = [
    dict(id=cid, name=name, armor=armor, primary=primary, role=role,
         color=color, mainhand=main.split(), offhand=off.split())
    for cid, name, armor, primary, role, color, main, off in [
        ('warrior', 'Warrior', 'plate', 'str', 'melee', '#C9A27E',
         'sword axe mace greatsword greataxe warhammer polearm', 'shield sword axe mace'),
        ('paladin', 'Paladin', 'plate', 'str', 'melee', '#F29AC4',
         'sword mace axe greatsword warhammer polearm', 'shield tome'),
        ('deathknight', 'Death Knight', 'plate', 'str', 'melee', '#F0667A',
         'sword axe mace greatsword greataxe warhammer polearm', 'sword axe mace'),
        ('hunter', 'Hunter', 'mail', 'agi', 'ranged', '#A8D47E',
         'bow crossbow gun polearm', ''),
        ('shaman', 'Shaman', 'mail', 'int', 'caster', '#4F9BF2',
         'mace axe fist staff dagger', 'shield mace axe fist orb'),
        ('rogue', 'Rogue', 'leather', 'agi', 'melee', '#F7EB72',
         'dagger sword fist axe mace', 'dagger sword fist'),
        ('monk', 'Monk', 'leather', 'agi', 'melee', '#33EBA2',
         'staff polearm fist sword mace axe', 'fist sword mace axe'),
        ('druid', 'Druid', 'leather', 'int', 'caster', '#F98B2E',
         'staff polearm mace dagger fist', 'tome orb'),
        ('demonhunter', 'Demon Hunter', 'leather', 'agi', 'melee', '#C873E6',
         'warglaive fist sword axe', 'warglaive fist'),
        ('priest', 'Priest', 'cloth', 'int', 'caster', '#F2F0EA',
         'staff wand mace dagger', 'tome orb'),
        ('mage', 'Mage', 'cloth', 'int', 'caster', '#5CCDEA',
         'staff wand sword dagger', 'tome orb'),
        ('warlock', 'Warlock', 'cloth', 'int', 'caster', '#9A9BF0',
         'staff wand dagger sword', 'tome orb'),
    ]
]
CLASS_BY_ID = {c['id']: c for c in CLASSES}
TWO_HAND = 'greatsword greataxe warhammer polearm staff bow crossbow gun'.split()
OFFHAND_ONLY = ('shield', 'tome', 'orb')
SLOTS = 'head shoulders back chest hands legs feet mainhand offhand'.split()
ARMOR_SLOTS = ('head', 'shoulders', 'chest', 'hands', 'legs', 'feet')
RARITIES = [
    dict(id=rid, name=name, color=color, index=index)
    for index, (rid, name, color) in enumerate([
        ('basic', 'Basic', '#FFFFFF'), ('common', 'Common', '#1EFF00'),
        ('rare', 'Rare', '#0070DD'), ('epic', 'Epic', '#A64DF0'),
        ('legendary', 'Legendary', '#FF8000'),
    ])
]
RARITY_IDS = [r['id'] for r in RARITIES]
RARITY_BONUS = dict(basic=0, common=3, rare=7, epic=13, legendary=20)
RARITY_MULT = dict(basic=1.00, common=1.12, rare=1.28, epic=1.48, legendary=1.75)
SECONDARY_COUNT = dict(basic=0, common=1, rare=2, epic=2, legendary=3)
SECONDARIES = ('crit', 'haste', 'mastery', 'versatility')
STAT_KEYS = ('primary', 'stamina', *SECONDARIES, 'armor', 'damage')
SLOT_WEIGHT = dict(head=.80, shoulders=.70, back=.50, chest=1., hands=.65,
                   legs=.90, feet=.65, mainhand=.65, offhand=.50)
ARMOR_MULT = dict(cloth=.6, leather=1., mail=1.4, plate=2., cloak=.6)
COURSE_DIFFICULTY = dict(python=1, foundations=1, web=1, backend=2, data=2, reliability=2,
                         harness=2, interactive=2, pytorch=2, tensorflow=2,
                         modern=3, rl=3, cuda=3)
LESSONS_BY_COURSE = {
    c['id']: [lesson for lesson in LESSONS if lesson['course'] == c['id']]
    for c in COURSES
}
LESSON_TIERS = {
    lesson['id']: min(5, COURSE_DIFFICULTY.get(cid, 2) +
                      (2 if index == len(lessons) - 1 else
                       1 if index >= len(lessons) / 2 else 0))
    for cid, lessons in LESSONS_BY_COURSE.items()
    for index, lesson in enumerate(lessons)
}
PATH_TIERS = {c['id']: min(5, COURSE_DIFFICULTY.get(c['id'], 2) + 3) for c in COURSES}
CHEST_TIERS = [
    dict(tier=tier, name=name, count=count, ilvl=[lo, hi], floor=floor,
         rates=dict(zip(RARITY_IDS, rates)))
    for tier, name, count, lo, hi, floor, rates in [
        (1, 'Worn Footlocker', '1', 8, 14, None, [65, 28, 6.2, .75, .05]),
        (2, 'Ironbound Strongbox', '1–2', 16, 24, None, [42, 40, 15, 2.8, .2]),
        (3, 'Runed Coffer', '1–2', 26, 36, None, [18, 44, 31, 6.4, .6]),
        (4, 'Infernal Reliquary', '2', 38, 50, 'rare', [6, 32, 47, 13.5, 1.5]),
        (5, 'Gilded Dragon Hoard', '2–3', 52, 64, 'rare', [0, 18, 54, 24, 4]),
    ]
]
TIER_BY_ID = {t['tier']: t for t in CHEST_TIERS}
ARMOR_NOUNS = {
    'cloth': ['Hood/Cowl/Circlet', 'Mantle/Amice', 'Robe/Vestments',
              'Handwraps/Gloves', 'Leggings/Trousers', 'Slippers/Sandals'],
    'leather': ['Cap/Mask/Headguard', 'Spaulders/Shoulderpads', 'Tunic/Jerkin/Vest',
                'Grips/Gloves', 'Breeches/Legguards', 'Boots/Treads'],
    'mail': ['Coif/Helm', 'Pauldrons/Shoulderguards', 'Hauberk/Chainmail',
             'Gauntlets/Handguards', 'Legguards/Kilt', 'Sabatons/Greaves'],
    'plate': ['Helm/Greathelm/Faceguard', 'Pauldrons/Spaulders',
              'Breastplate/Chestguard/Warplate', 'Gauntlets',
              'Legplates/Greaves', 'Sabatons/Warboots'],
}
NOUNS = {base: {slot: names.split('/') for slot, names in zip(ARMOR_SLOTS, groups)}
         for base, groups in ARMOR_NOUNS.items()}
BASE_NOUNS = {
    base: names.split('/') for base, names in dict(
        cloak='Cloak/Cape/Drape/Shroud', sword='Shortsword/Longsword/Blade/Saber',
        greatsword='Greatsword/Claymore/Zweihander', axe='Hatchet/Axe/Cleaver',
        greataxe='Greataxe/Reaver/Executioner', mace='Mace/Cudgel/Flanged Mace',
        warhammer='Warhammer/Maul', dagger='Dagger/Dirk/Stiletto/Kris',
        fist='Claws/Knuckles/Talons', warglaive='Warglaive',
        polearm='Halberd/Spear/Glaive/Pike', staff='Staff/Stave/Quarterstaff/Spire',
        wand='Wand/Rod/Scepter', bow='Shortbow/Longbow/Recurve Bow',
        crossbow='Crossbow/Arbalest', gun='Rifle/Blunderbuss/Hand Cannon',
        shield='Buckler/Shield/Bulwark/Aegis', tome='Tome/Grimoire/Codex',
        orb='Orb/Focus/Lantern').items()
}
BASIC_MATERIALS = dict(cloth=['Linen', 'Wool'], leather=['Hide', 'Leather'],
                       mail=['Chain', 'Scale'], plate=['Iron', 'Steel'])
COMMON_MATERIALS = dict(cloth=['Silk', 'Wool'], leather=['Leather', 'Wolfhide'],
                        mail=['Chain', 'Scale'], plate=['Steel', 'Iron'])
ANIMALS = dict(Tiger='crit', Falcon='haste', Owl='mastery', Bear='versatility')
RARE_PREFIXES = {
    'cloth': 'Moonsilk Duskwoven Starlit Runebound'.split(),
    'leather': 'Thunderhide Shadowstalker Wolfsbane Nightprowl'.split(),
    'mail': 'Stormforged Ironscale Wyrmscale Tidecaller'.split(),
    'plate': 'Frostguard Sunforged Lionheart Bulwark'.split(),
}
RARE_GENERIC = 'Stormforged Runebound Sunfire Frostbite Wolfsbane Starlit'.split()
EPIC_PREFIXES = ('Doomforged Bloodfire Shadowflame Dreadsteel Hellforged '
                 'Soulrender Nightfall Dragonbone').split()
EPIC_SUFFIXES = ['the Ashen Legion', 'the Eternal Pyre', 'Ruin', 'the Hollow King',
                 'the Void', 'Endless Night', 'the Blood Moon']
# Each epic suffix carries its own line of lore, so two epics from one chest read differently.
EPIC_FLAVOR = {
    'the Ashen Legion': 'Issued to the legion that held the pass after the city burned.',
    'the Eternal Pyre': 'Still warm, though the forge that made it went cold an age ago.',
    'Ruin': 'Recovered from the rubble of a keep that no map still shows.',
    'the Hollow King': 'Its last owner served a king who never let anyone see his face.',
    'the Void': 'Light bends slightly around its edges, as if something is missing.',
    'Endless Night': 'Made for guards who stood watch through a winter without dawn.',
    'the Blood Moon': 'Hunters wore it under the red moon, when the wolves came down.',
}
EFFECT_DETAILS = [
    ('inferno', 'Inferno',
     'Your attacks and abilities ignite enemies, burning them for 40% extra damage over 3 sec.',
     ['Emberheart', 'Cinderfall', 'Pyreborn'], 'the Burning Sun',
     'Ash from the Cinderpeak forges is sealed within the runes.'),
    ('stormcall', 'Stormcall',
     'Every 4th attack releases chain lightning that leaps to 3 enemies.',
     ['Thunderwake', 'Stormrend', 'Skysplitter'], 'the Endless Tempest',
     'Rain hisses against its blue runes.'),
    ('bloodsong', 'Bloodsong', 'Heal for 8% of all damage you deal.',
     ['Crimson Hymn', 'Sanguine Oath', 'Bloodsong'], 'the Red Moon',
     'Dried blood fills the grooves of an old oath.'),
    ('riftwalk', 'Riftwalk',
     'Your abilities have a 25% chance to instantly reset their cooldown.',
     ['Rifthollow', 'Voidstep', 'Shardweaver'], 'the Shattered Sky',
     'Its shadow falls a heartbeat before it moves.'),
    ('dawnfire', 'Dawnfire',
     'Slain enemies erupt in a holy nova that damages nearby foes.',
     ['Dawnbreaker', 'Lightsworn', 'Solace'], 'the First Light',
     'Burned chapel cloth is bound beneath the seal.'),
    ('wintergrasp', "Winter's Grasp",
     'Your attacks slow enemies by 30%. Slowed enemies take 15% more damage.',
     ['Rimecaller', 'Frostwake', 'Glacial Oath'], 'the Long Winter',
     'Frost gathers where the last bearer gripped it.'),
    ('phoenix', 'Phoenix Rebirth',
     'Once per battle, a fatal blow instead restores you to 50% health.',
     ['Ashen Phoenix', 'Everflame', 'Rebirth'], 'the Undying Flame',
     "The maker's ashes lie beneath a red stone."),
    ('galeforce', 'Galeforce',
     '+25% movement speed. Your dashes and blinks leave a damaging cyclone.',
     ['Galeforce', 'Windreaver', "Zephyr's Edge"], 'the Wild Wind',
     'Dust circles it even in a closed room.'),
    ('kingslayer', 'Kingslayer', 'Deal 35% more damage to elite and boss enemies.',
     ['Kingsbane', 'Crownbreaker', "Tyrant's End"], 'Fallen Kings',
     'Five notches mark the kings it brought down.'),
    ('starward', 'Starward Aegis',
     'Every 8 sec, gain a shield that absorbs 15% of your maximum health.',
     ['Starward', 'Astral Bulwark', 'Celestine'], 'the Silver Stars',
     'Its silver runes shine through soot and blood.'),
]
EFFECTS = [dict(id=eid, name=name, text=text) for eid, name, text, *_ in EFFECT_DETAILS]
STARTER_WEAPONS = dict(
    warrior=['sword', 'shield'], paladin=['mace', 'shield'], deathknight=['greatsword'],
    hunter=['bow'], shaman=['mace', 'shield'], rogue=['dagger', 'dagger'], monk=['staff'],
    druid=['staff'], demonhunter=['warglaive', 'warglaive'], priest=['staff'],
    mage=['staff'], warlock=['staff'])
# Expected Power and Health of a hero who reaches each stage at the planned pace, measured
# with `npm run game:sim`. Enemies scale with these targets, so a hero at the target finds each
# stage about as hard as the first, and a hero above it wins sooner. Boss health is the number of
# seconds a hero at the target needs to bring the boss down, times Power.
STAGE_TARGETS = [(36, 480), (55, 670), (100, 1030), (180, 1700), (240, 2160),
                 (320, 2800), (360, 2950), (410, 3300), (450, 3600), (490, 3900)]
BOSS_HP_PER_POWER = [125, 170, 185, 200, 215, 200, 210, 220, 225, 230]
ABYSS_GROWTH = 1.25
ABYSS_TARGET_GROWTH = (1.12, 1.08)
MAX_BATTLE_DAMAGE = 2**53 - 1
CAMPAIGN_STAGES = [
    dict(stage=stage, name=name, boss=boss)
    for stage, (name, boss) in enumerate([
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
    ], 1)
]
ABYSS_BOSSES = ('Tyrant', 'Behemoth', 'Herald', 'Warden', 'Devourer')
BATTLE_COLUMNS = ('id', 'stage', 'started', 'finished', 'outcome', 'damage', 'kills', 'seconds')
NEXT_BATTLE = 'Finish a lesson, project walkthrough or reading to earn your next battle.'
# A fight started this recently blocks passive changes; an older one was left without a result.
BATTLE_LOCK = timedelta(minutes=15)


def catalog():
    return dict(races=RACES, classes=CLASSES, slots=SLOTS, rarities=RARITIES,
                chestTiers=CHEST_TIERS, lessonTiers=LESSON_TIERS, pathTiers=PATH_TIERS,
                effects=EFFECTS, twoHand=TWO_HAND, tree=game_tree.catalog())


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def stage_names(stage):
    if stage <= 10:
        entry = CAMPAIGN_STAGES[stage - 1]
        return entry['name'], entry['boss']
    return (f'The Abyss · Depth {stage - 10}',
            'Abyssal ' + ABYSS_BOSSES[(stage - 11) % len(ABYSS_BOSSES)])


def stage_target(stage):
    """Expected (Power, Health) on reaching a stage; the Abyss keeps rising past the curriculum."""
    if stage <= 10:
        return STAGE_TARGETS[stage - 1]
    power, health = STAGE_TARGETS[-1]
    return (round(power * ABYSS_TARGET_GROWTH[0]**(stage - 10)),
            round(health * ABYSS_TARGET_GROWTH[1]**(stage - 10)))


def boss_hp(stage):
    if stage <= 10:
        return int(round(BOSS_HP_PER_POWER[stage - 1] * STAGE_TARGETS[stage - 1][0], -2))
    return round(boss_hp(10) * ABYSS_GROWTH**(stage - 10))


def campaign(meta):
    stage = meta['stage']
    name, boss = stage_names(stage)
    hp = boss_hp(stage)
    # Damage saved before a boss health change can exceed the new total; the boss keeps 1 health.
    damage = min(meta['bossDamage'], hp - 1)
    power, health = stage_target(stage)
    first_power, first_health = STAGE_TARGETS[0]
    return dict(stage=stage, stageName=name, bossName=boss, bossHp=hp,
                bossDamage=damage, bossRemaining=hp - damage,
                targetPower=power, targetHealth=health,
                enemyHealth=power / first_power, enemyDamage=health / first_health)


def practice_stages(reached):
    """Enemy strength for the practice arena at each stage reached so far; nothing here is saved."""
    out = []
    for stage in range(1, reached + 1):
        entry = campaign(dict(stage=stage, bossDamage=0))
        out.append({k: entry[k] for k in ('stage', 'stageName', 'bossHp', 'enemyHealth', 'enemyDamage')})
    return out


def boss_chest(stage, finished):
    name, boss = stage_names(stage)
    return chest(f'boss:{stage}', 'boss', min(5, 2 + (stage - 1) // 3),
                 boss + ' defeated', f'Stage {stage} · {name}', finished)


def boss_chests(db):
    return [boss_chest(stage, finished) for stage, finished in db.execute(
        "SELECT stage,finished FROM game_battles WHERE outcome='victory'")]


EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def from_millis(value):
    # Existing progress accepts JS-safe integers, including dates beyond year 9999.
    # Add to the epoch instead of datetime.fromtimestamp, which Windows rejects for far-future dates.
    seconds = min(max(value / 1000, 0), 253402300799)
    return (EPOCH + timedelta(seconds=seconds)).isoformat()


def chest(source, kind, tier, title, subtitle, earned_at):
    return dict(source=source, kind=kind, tier=tier, tierName=TIER_BY_ID[tier]['name'],
                title=title, subtitle=subtitle, earnedAt=earned_at, opened=False,
                openedAt=None, itemIds=[])


PROJECT_TIERS = {'Start small': 2, 'Build next': 3, 'Capstone': 4}


def project_chest(project, saved):
    """A project is finished when every task (or walkthrough step) is ticked; the stretch task
    does not count. The level sets the tier, and one more tier, up to 5, needs a recorded
    passing check on every task that has a check."""
    tasks = project.get('tasks') or []
    count = len(tasks) or len(project.get('steps', []))
    if not count or not set(range(count)).issubset(saved.get('reviewed', [])):
        return None
    tier = PROJECT_TIERS.get(project.get('level'), 3)
    checked = [t['id'] for t in tasks if t.get('verify', {}).get('check')]
    passed = saved.get('tasks') or {}
    bonus = bool(checked) and all((passed.get(tid) or {}).get('verifiedAt') for tid in checked)
    subtitle = ('Project · every check passed' if bonus else 'Project') if tasks else 'Project walkthrough'
    return chest('project:' + project['id'], 'project', min(5, tier + bonus), project['title'],
                 subtitle, from_millis(saved.get('updatedAt', 0)))


def solution_first(shown, passed):
    """True when a lesson's solution was shown before the lesson was first passed."""
    if not shown:
        return False
    try:
        return datetime.fromisoformat(shown) <= datetime.fromisoformat(passed)
    except (TypeError, ValueError):
        return False


def earned_chests(progress, hero=None):
    """Derive eligibility afresh; the database only remembers opened sources."""
    result = []
    completed = progress.get('completed', {})
    revealed = progress.get('revealed', {})
    if hero:
        result.append(chest('welcome', 'welcome', 1, 'A gift for new heroes', '',
                            hero['createdAt']))
    for course in COURSES:
        lessons = LESSONS_BY_COURSE[course['id']]
        for lesson in lessons:
            if lesson['id'] in completed:
                at = completed[lesson['id']]['at']
                tier, subtitle = LESSON_TIERS[lesson['id']], course['title']
                if solution_first(revealed.get(lesson['id']), at):
                    tier, subtitle = max(1, tier - 1), subtitle + ' · solution shown first'
                result.append(chest('lesson:' + lesson['id'], 'lesson', tier, lesson['title'],
                                    subtitle, at))
        if lessons and all(lesson['id'] in completed for lesson in lessons):
            latest = max((completed[lesson['id']]['at'] for lesson in lessons),
                         key=lambda at: datetime.fromisoformat(at))
            result.append(chest('path:' + course['id'], 'path', PATH_TIERS[course['id']],
                                course['title'] + ' mastered', 'Learning path complete', latest))
    for project in progress.get('projects', []):
        saved = progress.get('projectState', {}).get(project['id'], {})
        reward = project_chest(project, saved)
        if reward:
            result.append(reward)
    for old in progress.get('retiredProjects', []):
        # A replaced catalog entry keeps the chest it earned: three steps, tier 3, as before.
        saved = progress.get('projectState', {}).get(old['id'], {})
        if old['steps'] and set(range(old['steps'])).issubset(saved.get('reviewed', [])):
            result.append(chest('project:' + old['id'], 'project', 3, old['title'],
                                'Retired project', from_millis(saved.get('updatedAt', 0))))
    for guide in progress.get('guides', []):
        saved = progress.get('readingState', {}).get(guide['bookId'], {})
        if guide['id'] in saved.get('completed', []):
            result.append(chest('reading:' + guide['id'], 'reading', 2, guide['title'],
                                guide['bookTitle'], from_millis(saved.get('updatedAt', 0))))
    return sorted(result, key=lambda c: (datetime.fromisoformat(c['earnedAt']), c['source']))


def roll_rarity(tier, luck, rng):
    """Return a rarity and fresh pity counters, counting exactly one item roll."""
    weights = list(TIER_BY_ID[tier]['rates'].values())
    weights[4] += .05 * luck['sinceLegendary']
    weights[3] += .25 * luck['sinceEpic']
    rarity = rng.choices(RARITY_IDS, weights=weights, k=1)[0]
    if luck['sinceLegendary'] + 1 >= 90:
        rarity = 'legendary'
    elif luck['sinceEpic'] + 1 >= 40 and rarity not in ('epic', 'legendary'):
        rarity = 'epic'
    return rarity, dict(
        sinceEpic=0 if rarity in ('epic', 'legendary') else luck['sinceEpic'] + 1,
        sinceLegendary=0 if rarity == 'legendary' else luck['sinceLegendary'] + 1)


def slot_weights(class_id, tier, equipment, rolled=()):
    """Equipment maps slots to item objects here, independent of persistence IDs."""
    cls = CLASS_BY_ID[class_id]
    result = {}
    for slot in SLOTS:
        if slot == 'offhand' and not cls['offhand']:
            continue
        current = equipment.get(slot)
        weight = 2.5 if current is None else (
            1.6 if current['ilvl'] < TIER_BY_ID[tier]['ilvl'][0] else 1.)
        if slot == 'mainhand':
            weight *= 1.3
        elif slot == 'offhand':
            weight *= .7
            if equipment.get('mainhand', {}).get('twoHand'):
                weight *= .4
        if slot in rolled:
            weight *= .15
        result[slot] = weight
    return result


def choose_slot_base(class_id, tier, equipment, rolled, rng):
    cls = CLASS_BY_ID[class_id]
    weights = slot_weights(class_id, tier, equipment, rolled)
    slot = rng.choices(list(weights), weights=list(weights.values()), k=1)[0]
    if slot in ARMOR_SLOTS:
        base = cls['armor']
    elif slot == 'back':
        base = 'cloak'
    else:
        base = rng.choice(cls[slot])
    return slot, base


def item_name(slot, base, rarity, owned_effects, rng):
    noun = rng.choice(NOUNS[base][slot] if base in NOUNS else BASE_NOUNS[base])
    if rarity == 'basic':
        adjectives = ['Simple', 'Crude', 'Old']
        if base in ('cloth', 'leather', 'cloak'):
            adjectives += ['Worn', 'Frayed', 'Patched']
        elif base in ('mail', 'plate', 'sword', 'axe', 'mace', 'greatsword', 'greataxe',
                      'warhammer', 'polearm', 'dagger', 'fist', 'warglaive', 'shield', 'gun'):
            adjectives += ['Dented', 'Rusty']
        material = rng.choice(BASIC_MATERIALS.get(base, ['']))
        name = ' '.join(part for part in [rng.choice(adjectives), material, noun] if part)
        return name, None, '', None
    if rarity == 'common':
        animal = rng.choice(list(ANIMALS))
        adjective = rng.choice('Sturdy Fine Polished Reinforced Balanced Keen Stout'.split())
        material = rng.choice(COMMON_MATERIALS.get(base, ['']))
        name = ' '.join(part for part in [adjective, material, noun, 'of the', animal] if part)
        return name, None, '', ANIMALS[animal]
    if rarity == 'rare':
        return rng.choice(RARE_PREFIXES.get(base, RARE_GENERIC)) + ' ' + noun, None, '', None
    if rarity == 'epic':
        suffix = rng.choice(EPIC_SUFFIXES)
        return f'{rng.choice(EPIC_PREFIXES)} {noun} of {suffix}', None, EPIC_FLAVOR[suffix], None
    choices = [e for e in EFFECT_DETAILS if e[0] not in owned_effects] or EFFECT_DETAILS
    eid, title, text, names, theme, flavor = rng.choice(choices)
    return (f'{rng.choice(names)}, {noun} of {theme}',
            dict(id=eid, name=title, text=text), flavor, None)


def generate_item(class_id, slot, base, rarity, ilvl, rng, source='', obtained_at='',
                  owned_effects=(), starter=False):
    """Build an item without a database ID; all randomness is supplied by the caller."""
    name, effect, flavor, secondary = item_name(slot, base, rarity, owned_effects, rng)
    if starter:
        noun = rng.choice(NOUNS[base][slot] if base in NOUNS else BASE_NOUNS[base])
        name = "Recruit's " + noun
    two_hand = base in TWO_HAND
    weight = 1. if slot == 'mainhand' and two_hand else SLOT_WEIGHT[slot]
    mult = RARITY_MULT[rarity]
    budget = ilvl * mult * weight
    stats = dict.fromkeys(STAT_KEYS, 0)
    stats['primary'] = round(budget * (.75 if base in ('tome', 'orb') else .55))
    stats['stamina'] = round(budget * .80)
    chosen = [secondary] if secondary else rng.sample(SECONDARIES, SECONDARY_COUNT[rarity])
    for stat, factor in zip(chosen, (.30, .22, .18)):
        stats[stat] = round(budget * factor)
    armor_bonus = 1 + .08 * RARITY_IDS.index(rarity)
    if slot in ARMOR_SLOTS or slot == 'back':
        stats['armor'] = round(ilvl * ARMOR_MULT[base] * weight * armor_bonus)
    elif base == 'shield':
        stats['armor'] = round(ilvl * 3.2 * armor_bonus)
    if slot in ('mainhand', 'offhand') and base not in OFFHAND_ONLY:
        factor = (2.1 if base in ('bow', 'crossbow', 'gun') else 2.3 if two_hand else
                  1.2 if base == 'dagger' else 1.4 if base == 'wand' else 1.35)
        stats['damage'] = round(ilvl * factor * mult)
    return dict(slot=slot, base=base, rarity=rarity, ilvl=ilvl, name=name,
                primaryStat=CLASS_BY_ID[class_id]['primary'], twoHand=two_hand, stats=stats,
                effect=effect, flavor=flavor, seed=rng.randint(0, 2**31 - 1),
                source=source, obtainedAt=obtained_at, equipped=False)


def starter_kit(class_id, rng, obtained_at):
    slots = [(slot, CLASS_BY_ID[class_id]['armor']) for slot in ('chest', 'legs', 'feet')]
    slots += list(zip(('mainhand', 'offhand'), STARTER_WEAPONS[class_id]))
    return [generate_item(class_id, slot, base, 'basic', 5, rng, 'starter', obtained_at,
                          starter=True) for slot, base in slots]


def roll_chest(class_id, tier, equipment, owned_effects, luck, rng, source='', obtained_at=''):
    config = TIER_BY_ID[tier]
    count = (1 if tier == 1 else 1 + (rng.random() < .3) if tier == 2 else
             1 + (rng.random() < .5) if tier == 3 else 2 if tier == 4 else
             2 + (rng.random() < .5))
    rolled = []
    effects = set(owned_effects)
    counters = dict(luck)
    for _ in range(count):
        rarity, counters = roll_rarity(tier, counters, rng)
        slot, base = choose_slot_base(class_id, tier, equipment, [i['slot'] for i in rolled], rng)
        ilvl = rng.randint(*config['ilvl']) + RARITY_BONUS[rarity]
        item = generate_item(class_id, slot, base, rarity, ilvl, rng, source, obtained_at, effects)
        rolled.append(item)
        if item['effect']:
            effects.add(item['effect']['id'])
    floor = config['floor']
    if floor and all(RARITY_IDS.index(i['rarity']) < RARITY_IDS.index(floor) for i in rolled):
        first = rolled[0]
        ilvl = rng.randint(*config['ilvl']) + RARITY_BONUS[floor]
        rolled[0] = generate_item(class_id, first['slot'], first['base'], floor, ilvl, rng,
                                  source, obtained_at, effects)
    return rolled, counters


def ensure_schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS game_hero '
               '(id INTEGER PRIMARY KEY CHECK (id=1), data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS game_items '
               '(id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS game_equipment '
               '(slot TEXT PRIMARY KEY, item INTEGER NOT NULL UNIQUE REFERENCES game_items(id))')
    db.execute('CREATE TABLE IF NOT EXISTS game_chests '
               '(source TEXT PRIMARY KEY, data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS game_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS game_battles '
               '(id INTEGER PRIMARY KEY AUTOINCREMENT, stage INTEGER NOT NULL, '
               'started TEXT NOT NULL, finished TEXT, outcome TEXT NOT NULL DEFAULT \'active\', '
               'damage INTEGER NOT NULL DEFAULT 0, kills INTEGER NOT NULL DEFAULT 0, '
               'seconds INTEGER NOT NULL DEFAULT 0)')
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS game_boss_kills "
               "ON game_battles(stage) WHERE outcome='victory'")
    # Revision 1's difficulty records do not carry into the campaign.
    if db.execute("SELECT 1 FROM game_meta WHERE key='records'").fetchone():
        db.execute("DELETE FROM game_meta WHERE key='records'")


def metadata(db):
    defaults = dict(sinceEpic=0, sinceLegendary=0, enabled=True, stage=1, bossDamage=0,
                    passives={'v': 1, 'nodes': []})
    placeholders = ','.join('?' for _ in defaults)
    saved = {key: json.loads(value) for key, value in db.execute(
        f'SELECT key,value FROM game_meta WHERE key IN ({placeholders})', tuple(defaults))}
    return {**defaults, **saved}


def put_meta(db, key, value):
    db.execute('INSERT INTO game_meta VALUES (?,?) '
               'ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, json.dumps(value)))


def saved_hero(db):
    row = db.execute('SELECT data FROM game_hero WHERE id=1').fetchone()
    return json.loads(row[0]) if row else None


def inventory(db):
    equipment = dict(db.execute('SELECT slot,item FROM game_equipment'))
    items = [{**json.loads(data), 'id': iid, 'equipped': iid in equipment.values()}
             for iid, data in db.execute('SELECT id,data FROM game_items ORDER BY id DESC')]
    return items, equipment


@contextmanager
def snapshot(db):
    """Use one read snapshot, or the caller's existing write transaction."""
    if db.in_transaction:
        yield
    else:
        with db:
            db.execute('BEGIN')
            yield


def export(db):
    """Lossless game backup: all opened sources, without the UI's history limit."""
    with snapshot(db):
        items, equipment = inventory(db)
        chests = [json.loads(r[0]) for r in db.execute('SELECT data FROM game_chests')]
        battles = [dict(zip(BATTLE_COLUMNS, row)) for row in db.execute(
            'SELECT id,stage,started,finished,outcome,damage,kills,seconds '
            'FROM game_battles ORDER BY id DESC')]
        return dict(hero=saved_hero(db), items=items, equipment=equipment,
                    chests=chests, meta=metadata(db), battles=battles)


def hero_level(progress):
    xp = sum(c['xp'] for c in progress.get('completed', {}).values())
    return xp, min(60, 1 + xp // 100)


def paths_mastered(progress):
    completed = progress.get('completed', {})
    return sum(1 for lessons in LESSONS_BY_COURSE.values()
               if lessons and all(lesson['id'] in completed for lesson in lessons))


def passive_points(progress):
    """One point per level after the first, and one per mastered learning path."""
    return hero_level(progress)[1] - 1 + paths_mastered(progress)


def saved_passives(meta):
    """The stored node ids, or None when the stored value is not a version 1 allocation."""
    value = meta.get('passives')
    if (not isinstance(value, dict) or value.get('v') != 1 or not isinstance(value.get('nodes'), list)
            or not all(isinstance(nid, str) for nid in value['nodes'])):
        return None
    return value['nodes']


def passives(meta, hero, progress):
    """The allocation in effect. One that no longer fits the tree or the points is refunded whole.
    settle_passives stores the refund, and `refunded` stays until the next allocation is saved."""
    if not hero:
        return None
    earned = passive_points(progress)
    start = game_tree.START_BY_CLASS[hero['class']]
    nodes = saved_passives(meta)
    reason = 'changed' if nodes is None else None
    if nodes:
        nodes = list(dict.fromkeys([start, *nodes]))
        problem = game_tree.problem(hero['class'], nodes, earned)
        reason = problem and ('points' if problem == 'points' else 'changed')
    elif nodes == [] and meta['passives'].get('refunded') in ('changed', 'points'):
        reason = meta['passives']['refunded']
    allocated = [start] if reason or not nodes else sorted(nodes)
    spent = len(allocated) - 1
    return dict(allocated=allocated, points=dict(earned=earned, spent=spent, available=earned - spent),
                refunded=reason)


def settle_passives(db, hero, progress):
    """Store the refund of a saved build that no longer fits, so that it stays refunded when the points come back.
    Points fall only when an update changes the curriculum or the tree, so the server calls this at startup.
    Each game action calls it too, before it runs."""
    if not hero:
        return
    meta = metadata(db)
    reason = passives(meta, hero, progress)['refunded']
    refund = {'v': 1, 'nodes': [], 'refunded': reason}
    if reason and meta['passives'] != refund:
        put_meta(db, 'passives', refund)


def set_passives(db, hero, body, progress):
    allocated = game_tree.validate(hero['class'], body.get('allocated'), passive_points(progress))
    cutoff = datetime.now(timezone.utc) - BATTLE_LOCK
    for (started,) in db.execute("SELECT started FROM game_battles WHERE outcome='active'"):
        try:
            recent = datetime.fromisoformat(started) >= cutoff
        except (TypeError, ValueError):
            recent = False
        if recent:
            raise ValueError('Finish or retreat from your fight before changing passives.')
    start = game_tree.START_BY_CLASS[hero['class']]
    put_meta(db, 'passives', {'v': 1, 'nodes': [nid for nid in allocated if nid != start]})


def battle_counts(db, earned):
    used = db.execute('SELECT COUNT(*) FROM game_battles').fetchone()[0]
    count = len({c['source'] for c in earned})
    return dict(earned=count, used=used, available=max(0, count - used))


def battle_stats(db):
    row = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(outcome='victory'),0), COALESCE(SUM(kills),0), "
        "COALESCE(SUM(outcome='defeat'),0), COALESCE(SUM(damage),0), COALESCE(MAX(damage),0) "
        'FROM game_battles').fetchone()
    lifetime = dict(zip(('fights', 'victories', 'kills', 'deaths', 'totalDamage', 'bestDamage'), row))
    history = [dict(zip(('id', 'stage', 'outcome', 'damage', 'kills', 'seconds', 'finishedAt'), row))
               for row in db.execute(
                   "SELECT id,stage,outcome,damage,kills,seconds,finished FROM game_battles "
                   "WHERE outcome!='active' ORDER BY id DESC LIMIT 12")]
    return lifetime, history


def summary(db, progress):
    """Badge counts without loading items, catalogs, chest JSON, or battle history."""
    with snapshot(db):
        hero = saved_hero(db)
        meta = metadata(db)
        earned = earned_chests(progress, hero)
        sources = {c['source'] for c in earned}
        sources.update(f'boss:{row[0]}' for row in db.execute(
            "SELECT stage FROM game_battles WHERE outcome='victory'"))
        opened = {row[0] for row in db.execute('SELECT source FROM game_chests')}
        return dict(enabled=meta['enabled'], hero=hero is not None,
                    unopened=len(sources - opened), battles=battle_counts(db, earned)['available'],
                    stage=meta['stage'])


def state(db, progress):
    with snapshot(db):
        hero = saved_hero(db)
        items, equipment = inventory(db)
        meta = metadata(db)
        if hero:
            xp, level = hero_level(progress)
            hero = {**hero, 'xp': xp, 'level': level,
                    'levelProgress': 1. if level == 60 else (xp % 100) / 100}
        opened = {source: json.loads(data) for source, data in db.execute(
            'SELECT source,data FROM game_chests')}
        earned = earned_chests(progress, hero)
        unopened = [c for c in earned + boss_chests(db) if c['source'] not in opened]
        unopened.sort(key=lambda c: (datetime.fromisoformat(c['earnedAt']), c['source']))
        history = sorted(opened.values(), key=lambda c: (c['openedAt'], c['source']), reverse=True)
        lifetime, battle_history = battle_stats(db)
        return dict(enabled=meta['enabled'], hero=hero, items=items, equipment=equipment,
                    chests=dict(unopened=unopened, opened=history[:40]),
                    luck={k: meta[k] for k in ('sinceEpic', 'sinceLegendary')},
                    battles=battle_counts(db, earned),
                    campaign={**campaign(meta), 'stagesCleared': meta['stage'] - 1,
                              'stages': CAMPAIGN_STAGES, 'practice': practice_stages(meta['stage'])},
                    lifetime=lifetime, history=battle_history,
                    passives=passives(meta, hero, progress), catalog=catalog())


def store_item(db, item):
    data = {k: v for k, v in item.items() if k not in ('id', 'equipped')}
    iid = db.execute('INSERT INTO game_items (data) VALUES (?)', (json.dumps(data),)).lastrowid
    return {**item, 'id': iid, 'equipped': False}


def owned_item(db, iid):
    if type(iid) is not int or not 1 <= iid <= 2**63 - 1:
        raise ValueError('Choose a valid item.')
    row = db.execute('SELECT data FROM game_items WHERE id=?', (iid,)).fetchone()
    if not row:
        raise ValueError('You do not own that item.')
    return {**json.loads(row[0]), 'id': iid}


def validate_usable(class_id, item):
    cls = CLASS_BY_ID[class_id]
    slot, base = item.get('slot'), item.get('base')
    if slot in ARMOR_SLOTS:
        allowed = base == cls['armor']
    elif slot == 'back':
        allowed = base == 'cloak'
    elif slot in ('mainhand', 'offhand'):
        allowed = base in cls[slot]
    else:
        allowed = False
    if (not allowed or item.get('primaryStat') != cls['primary'] or
            item.get('twoHand') != (base in TWO_HAND)):
        raise ValueError('Your class cannot equip that item in that slot.')


def equip(db, hero, item):
    validate_usable(hero['class'], item)
    if item['slot'] == 'mainhand' and item['twoHand']:
        db.execute("DELETE FROM game_equipment WHERE slot='offhand'")
    elif item['slot'] == 'offhand':
        row = db.execute("SELECT i.data FROM game_items i JOIN game_equipment e "
                         "ON i.id=e.item WHERE e.slot='mainhand'").fetchone()
        if row and json.loads(row[0])['twoHand']:
            db.execute("DELETE FROM game_equipment WHERE slot='mainhand'")
    db.execute('INSERT INTO game_equipment VALUES (?,?) '
               'ON CONFLICT(slot) DO UPDATE SET item=excluded.item', (item['slot'], item['id']))


def equip_many(db, hero, ids):
    """Equip up to one item per slot, in order, all or nothing."""
    if (not isinstance(ids, list) or not 1 <= len(ids) <= len(SLOTS) or
            any(type(iid) is not int or not 1 <= iid <= 2**63 - 1 for iid in ids)):
        raise ValueError(f'Choose 1–{len(SLOTS)} items to equip.')
    items = [owned_item(db, iid) for iid in ids]
    if len({item['slot'] for item in items}) != len(items):
        raise ValueError('Choose at most one item for each slot.')
    for item in items:
        equip(db, hero, item)


def create_hero(db, body, rng):
    if saved_hero(db):
        raise ValueError('Retire your current hero first.')
    name = body.get('name')
    if not isinstance(name, str):
        raise ValueError('Enter a name.')
    name = name.strip()
    if not 2 <= len(name) <= 16:
        raise ValueError('Names must be 2–16 characters.')
    if not re.fullmatch(r"[A-Za-z][A-Za-z' -]*[A-Za-z]", name):
        raise ValueError('Use letters, spaces, hyphens or apostrophes; start and end with a letter.')
    if '  ' in name:
        raise ValueError('Use single spaces in names.')
    race, class_id = body.get('race'), body.get('class')
    if not isinstance(race, str) or race not in [r['id'] for r in RACES]:
        raise ValueError('Choose a known race.')
    if not isinstance(class_id, str) or class_id not in CLASS_BY_ID:
        raise ValueError('Choose a known class.')
    hero = dict(name=name, race=race, createdAt=utc_now(), **{'class': class_id})
    db.execute('INSERT INTO game_hero VALUES (1,?)', (json.dumps(hero),))
    for item in starter_kit(class_id, rng, hero['createdAt']):
        equip(db, hero, store_item(db, item))


def open_chest(db, hero, body, progress, rng):
    source = body.get('source')
    if not isinstance(source, str) or not source:
        raise ValueError('Choose an earned chest.')
    if db.execute('SELECT 1 FROM game_chests WHERE source=?', (source,)).fetchone():
        raise ValueError('This chest is already open.')
    earned = next((c for c in earned_chests(progress, hero) + boss_chests(db)
                   if c['source'] == source), None)
    if not earned:
        raise ValueError('This chest has not been earned.')
    items, equipment = inventory(db)
    by_id = {item['id']: item for item in items}
    equipped = {slot: by_id[iid] for slot, iid in equipment.items()}
    effects = {item['effect']['id'] for item in items if item['effect']}
    opened_at = utc_now()
    rolled, luck = roll_chest(hero['class'], earned['tier'], equipped, effects,
                              metadata(db), rng, source, opened_at)
    new_items = [store_item(db, item) for item in rolled]
    opened = {**earned, 'opened': True, 'openedAt': opened_at,
              'itemIds': [item['id'] for item in new_items]}
    db.execute('INSERT INTO game_chests VALUES (?,?)', (source, json.dumps(opened)))
    for key, value in luck.items():
        put_meta(db, key, value)
    return dict(chest=opened, items=new_items)


def start_battle(db, hero, progress):
    if not hero or battle_counts(db, earned_chests(progress, hero))['available'] == 0:
        raise ValueError(NEXT_BATTLE)
    current = campaign(metadata(db))
    now = utc_now()
    db.execute("UPDATE game_battles SET outcome='abandoned',finished=?,damage=0,kills=0,seconds=0 "
               "WHERE outcome='active'", (now,))
    iid = db.execute('INSERT INTO game_battles (stage,started) VALUES (?,?)',
                     (current['stage'], now)).lastrowid
    return dict(battle=dict(id=iid, **current))


def finish_battle(db, body):
    iid, outcome = body.get('battleId'), body.get('outcome')
    damage, kills, seconds = body.get('bossDamage'), body.get('kills'), body.get('seconds')
    if type(iid) is not int or not 1 <= iid <= 2**63 - 1:
        raise ValueError('Choose a valid battle.')
    if outcome not in ('victory', 'defeat', 'retreat'):
        raise ValueError('Choose victory, defeat or retreat.')
    if type(damage) is not int or not 0 <= damage <= MAX_BATTLE_DAMAGE:
        raise ValueError('Invalid boss damage.')
    if type(kills) is not int or not 0 <= kills <= 2000:
        raise ValueError('Kills must be between 0 and 2000.')
    if type(seconds) is not int or not 0 <= seconds <= 3600:
        raise ValueError('Battle time must be between 0 and 3600 seconds.')
    row = db.execute('SELECT stage,outcome FROM game_battles WHERE id=?', (iid,)).fetchone()
    if not row:
        raise ValueError('Battle not found.')
    if row[1] != 'active':
        raise ValueError('This battle has ended.')
    current = campaign(metadata(db))
    if row[0] != current['stage']:
        raise ValueError('This battle belongs to an earlier stage.')
    damage = min(damage, current['bossRemaining'])
    slain = damage >= current['bossRemaining']
    outcome = 'victory' if slain else 'defeat' if outcome == 'victory' else outcome
    now = utc_now()
    db.execute('UPDATE game_battles SET finished=?,outcome=?,damage=?,kills=?,seconds=? WHERE id=?',
               (now, outcome, damage, kills, seconds, iid))
    stage = current['stage'] + int(slain)
    put_meta(db, 'stage', stage)
    put_meta(db, 'bossDamage', 0 if slain else current['bossDamage'] + damage)
    reward = boss_chest(current['stage'], now) if slain else None
    return dict(result=dict(outcome=outcome, damage=damage, stageCleared=slain,
                            stage=stage, chest=reward))


def handle(db, action, body, progress, rng=None):
    """Serialize every mutation, including eligibility checks and the response snapshot."""
    if not isinstance(body, dict):
        raise ValueError('Expected an object.')
    if action not in ('hero', 'open', 'equip', 'equip-many', 'unequip', 'discard', 'settings',
                      'battle/start', 'battle/finish', 'retire', 'passives'):
        raise ValueError('Unknown game action.')
    if rng is None:
        rng = random.Random(secrets.randbits(64))
    with db:
        db.execute('BEGIN IMMEDIATE')
        extra = {}
        hero = saved_hero(db)
        settle_passives(db, hero, progress)
        if action == 'hero':
            create_hero(db, body, rng)
        elif action == 'settings':
            if type(body.get('enabled')) is not bool:
                raise ValueError('Choose on or off.')
            put_meta(db, 'enabled', body['enabled'])
        elif action == 'battle/start':
            extra = start_battle(db, hero, progress)
        elif action == 'retire':
            if body.get('confirm') != 'RETIRE':
                raise ValueError('Type RETIRE to retire your hero.')
            for table in ('game_equipment', 'game_items', 'game_chests', 'game_battles', 'game_hero'):
                db.execute('DELETE FROM ' + table)
            db.execute("DELETE FROM game_meta WHERE key!='enabled'")
        else:
            if not hero:
                raise ValueError('Create a hero first.')
            if action == 'open':
                extra = open_chest(db, hero, body, progress, rng)
            elif action == 'equip':
                equip(db, hero, owned_item(db, body.get('itemId')))
            elif action == 'equip-many':
                equip_many(db, hero, body.get('itemIds'))
            elif action == 'unequip':
                slot = body.get('slot')
                if slot not in SLOTS:
                    raise ValueError('Choose a valid equipment slot.')
                db.execute('DELETE FROM game_equipment WHERE slot=?', (slot,))
            elif action == 'discard':
                ids = body.get('itemIds')
                if (not isinstance(ids, list) or not 1 <= len(ids) <= 200 or
                        any(type(iid) is not int or not 1 <= iid <= 2**63 - 1 for iid in ids)):
                    raise ValueError('Choose 1–200 item IDs to discard.')
                equipped = {r[0] for r in db.execute('SELECT item FROM game_equipment')}
                for iid in set(ids):
                    owned_item(db, iid)
                    if iid in equipped:
                        raise ValueError('Unequip items before discarding them.')
                db.executemany('DELETE FROM game_items WHERE id=?', [(iid,) for iid in set(ids)])
            elif action == 'battle/finish':
                extra = finish_battle(db, body)
            elif action == 'passives':
                set_passives(db, hero, body, progress)
        return dict(game=state(db, progress), **extra)
