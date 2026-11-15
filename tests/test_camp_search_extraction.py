"""Focused synthetic checks for the offline search-suggestion prototype."""
from datetime import datetime, timedelta
from hashlib import sha256
import unittest

from eql_automation.camp_search_history import extract_search_suggestions

ZONE = 'Butcherblock Mountains'
START = datetime(2026, 11, 15, 0, 0, 0)
NPC = 'a bat'


def line(body, seconds=0):
    at = START + timedelta(seconds=seconds)
    return (at.strftime('[%a %b %d %H:%M:%S %Y] ') + body + '\n').encode()


def raw(*rows):
    return b''.join(line(body, at) for at, body in rows)


def extract(data, **kwargs):
    # Real engine import is unnecessary: this unit only tests pairing. Name
    # filtering is injected and the retained-artifact smoke uses the real rule.
    return extract_search_suggestions(data, ZONE,
        valid_name=lambda name: name.startswith(('a ', 'an ')), **kwargs)


def base():
    return raw((0, 'You have entered ' + ZONE + '.'), (1, 'Targeted (NPC): a bat'))


class SearchSuggestionsTests(unittest.TestCase):
    def test_exact_pair_has_distinct_provenance_and_no_authority(self):
        data = base() + line('You have slain a bat!', 3)
        result = extract(data)
        self.assertEqual(result['source_log_sha256'], sha256(data).hexdigest())
        row, = result['candidates']
        self.assertEqual(row['name'], NPC)
        self.assertEqual((row['levels'], row['pairs']), ([], []))
        self.assertFalse(row['current_target_authorized'])
        self.assertFalse(row['prior_consideration_claimed'])
        self.assertEqual(row['selection_kill_pairs'][0], {
            'zone_entry_line': 1, 'selection_line': 2, 'kill_line': 3,
            'selection_kind': 'NPC', 'selection_time': '2026-11-15T00:00:01',
            'kill_time': '2026-11-15T00:00:03', 'elapsed_seconds': 2})

    def test_pc_pet_and_other_npc_replace_selection(self):
        for kind, name in [('PC', NPC), ('Pet', NPC), ('NPC', 'a snake'), ('npc', NPC)]:
            with self.subTest(kind=kind, name=name):
                data = base() + line(f'Targeted ({kind}): {name}', 2) + line('You have slain a bat!', 3)
                self.assertEqual(extract(data)['candidates'], [])

    def test_mismatched_kill_consumes_selection(self):
        data = base() + line('You have slain a snake!', 2) + line('You have slain a bat!', 3)
        self.assertEqual(extract(data)['candidates'], [])

    def test_zone_and_log_boundaries_clear_selection(self):
        for boundary in ['You have entered ' + ZONE + '.', 'You have entered The Greater Faydark.',
                         "Logging to 'some-log' is now ON.", "Logging to '",
                         'LOADING, PLEASE WAIT...', 'You have been slain by a snake!']:
            with self.subTest(boundary=boundary):
                data = base() + line(boundary, 2) + line('You have slain a bat!', 3)
                self.assertEqual(extract(data)['candidates'], [])

    def test_logging_requires_new_zone_even_after_new_selection(self):
        data = base() + raw((2, "Logging to 'some-log' is now ON."),
            (3, 'Targeted (NPC): a bat'), (4, 'You have slain a bat!'))
        self.assertEqual(extract(data)['candidates'], [])

    def test_new_zone_reestablishes_continuity_and_line_numbers(self):
        data = base() + b'[invalid] You have entered another zone.\n' + raw(
            (3, 'You have entered ' + ZONE + '.'),
            (4, 'Targeted (NPC): a bat'), (5, 'You have slain a bat!'))
        row, = extract(data)['candidates']
        self.assertEqual(row['selection_kill_pairs'][0]['selection_line'], 5)
        self.assertEqual(row['selection_kill_pairs'][0]['kill_line'], 6)

    def test_pair_window_is_inclusive_150_seconds(self):
        self.assertEqual(len(extract(base() + line('You have slain a bat!', 151))['candidates']), 1)
        self.assertEqual(extract(base() + line('You have slain a bat!', 152))['candidates'], [])

    def test_excluded_protected_and_invalid_names_are_rejected(self):
        for name in ['a guard', 'a prisoner', 'a bat']:
            data = raw((0, 'You have entered ' + ZONE + '.'),
                (1, 'Targeted (NPC): ' + name), (2, 'You have slain ' + name + '!'))
            with self.subTest(name=name):
                self.assertEqual(extract(data, excluded=['A BAT'])['candidates'], [])
        self.assertEqual(extract_search_suggestions(base() + line('You have slain a bat!', 2),
            ZONE, valid_name=lambda name: False)['candidates'], [])

    def test_malformed_timestamp_or_bytes_breaks_zone_continuity(self):
        for malformed in [b'[Sun Nov 15 99:00:00 2026] Targeted (NPC): a bat\n',
                          b'broken line\n', b'\xff\n']:
            with self.subTest(malformed=malformed):
                data = base() + malformed + line('Targeted (NPC): a bat', 3) + line('You have slain a bat!', 4)
                self.assertEqual(extract(data)['candidates'], [])

    def test_unterminated_valid_looking_kill_is_not_evidence(self):
        data = base() + line('You have slain a bat!', 3).rstrip(b'\n')
        result = extract(data)
        self.assertEqual(result['candidates'], [])
        self.assertGreater(result['audit']['trailing_bytes_ignored'], 0)
        self.assertEqual(result['source_log_sha256'], sha256(data).hexdigest())

    def test_backwards_timestamp_breaks_continuity(self):
        self.assertEqual(extract(base() + line('You have slain a bat!', 0))['candidates'], [])

    def test_no_zone_and_kill_before_selection_supply_no_pair(self):
        self.assertEqual(extract(raw((1, 'Targeted (NPC): a bat'),
            (2, 'You have slain a bat!')))['candidates'], [])
        self.assertEqual(extract(raw((0, 'You have entered ' + ZONE + '.'),
            (1, 'You have slain a bat!'), (2, 'Targeted (NPC): a bat')))['candidates'], [])

    def test_duplicate_kill_and_miss_do_not_reuse_selection(self):
        data = base() + line('You have slain a bat!', 3) + line('You have slain a bat!', 4)
        self.assertEqual(len(extract(data)['candidates'][0]['selection_kill_pairs']), 1)
        data = base() + line('Target not found nearby.', 2) + line('You have slain a bat!', 3)
        self.assertEqual(extract(data)['candidates'], [])

    def test_matching_is_casefold_exact_not_substring(self):
        self.assertEqual(len(extract(base() + line('You have slain A Bat!', 3))['candidates']), 1)
        self.assertEqual(extract(base() + line('You have slain a batling!', 3))['candidates'], [])

    def test_non_owner_kill_or_chat_is_not_evidence(self):
        for body in ['a bat has been slain by Someone!', 'Someone says, You have slain a bat!',
                     'You have slain a bat! extra']:
            with self.subTest(body=body):
                self.assertEqual(extract(base() + line(body, 3))['candidates'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
