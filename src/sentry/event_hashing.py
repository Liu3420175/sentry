from __future__ import absolute_import

import re
import six

from hashlib import md5

from django.utils.encoding import force_bytes

HASH_RE = re.compile(r'^[0-9a-f]{32}$')
DEFAULT_FINGERPRINT_VALUES = frozenset(['{{ default }}', '{{default}}'])


DEFAULT_HINTS = {
    '!salt': 'a static salt',
}


def _calculate_contributes(values):
    for value in values or ():
        if not isinstance(value, GroupingComponent) or value.contributes:
            return True
    return False


class GroupingComponent(object):
    """A grouping component is a recursive structure that is flattened
    into components to make a hash for grouping purposes.
    """

    def __init__(self, id, hint=None, contributes=None, values=None):
        self.id = id
        if hint is None:
            hint = DEFAULT_HINTS.get(id)
        self.hint = hint
        if contributes is None:
            contributes = _calculate_contributes(values)
        self.contributes = contributes
        if values is None:
            values = []
        self.values = values

    def get_subcomponent(self, id):
        """Looks up a subcomponent by the id and returns the first or `None`."""
        for value in self.values:
            if isinstance(value, GroupingComponent) and value.id == id:
                return value

    def update(self, hint=None, contributes=None, values=None):
        """Updates an already existing component with new values."""
        if hint is not None:
            self.hint = hint
        if values is not None:
            if contributes is None:
                contributes = _calculate_contributes(values)
            self.values = values
        if contributes is not None:
            self.contributes = contributes

    def flatten_values(self):
        """Recursively walks the component and flattens it into a list of
        values.
        """
        rv = []
        if self.contributes:
            for value in self.values:
                if isinstance(value, GroupingComponent):
                    rv.extend(value.flatten_values())
                else:
                    rv.append(value)
        return rv

    def get_hash(self):
        """Returns the hash of the values if it contributes."""
        if self.contributes:
            return hash_from_values(self.flatten_values())

    def as_dict(self, skip_empty=False):
        """Converts the component tree into a dictionary."""
        rv = {
            'id': self.id,
            'contributes': self.contributes,
            'hint': self.hint,
            'values': []
        }
        for value in self.values:
            if isinstance(value, GroupingComponent):
                if skip_empty and not value.values:
                    continue
                rv['values'].append(value.as_dict(skip_empty=skip_empty))
            else:
                # this basically assumes that a value is only a primitive
                # and never an object or list.  This should be okay
                # because we verify this.
                rv['values'].append(value)
        return rv

    def __repr__(self):
        return 'GroupingComponent(%r, hint=%r, contributes=%r, values=%r)' % (
            self.id,
            self.hint,
            self.contributes,
            self.values,
        )


def hash_from_values(hash_bits):
    result = md5()
    for bit in hash_bits:
        result.update(force_bytes(bit, errors='replace'))
    return result.hexdigest()


def get_hashes_for_event(event):
    interfaces = event.get_interfaces()
    for interface in six.itervalues(interfaces):
        result = interface.compute_hashes(event.platform)
        if not result:
            continue
        return result
    return ['']


def get_hashes_from_fingerprint(event, fingerprint):
    if any(d in fingerprint for d in DEFAULT_FINGERPRINT_VALUES):
        default_hashes = get_hashes_for_event(event)
        hash_count = len(default_hashes)
    else:
        hash_count = 1

    hashes = []
    for idx in range(hash_count):
        result = []
        for bit in fingerprint:
            if bit in DEFAULT_FINGERPRINT_VALUES:
                result.extend(default_hashes[idx])
            else:
                result.append(bit)
        hashes.append(result)
    return hashes


def calculate_event_hashes(event):
    # If a checksum is set, use that one.
    checksum = event.data.get('checksum')
    if checksum:
        if HASH_RE.match(checksum):
            return [checksum]
        return [hash_from_values([checksum]), checksum]

    # Otherwise go with the new style fingerprint code
    fingerprint = event.data.get('fingerprint') or ['{{ default }}']
    return [hash_from_values(h) for h in get_hashes_from_fingerprint(event, fingerprint)]
