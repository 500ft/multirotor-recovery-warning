"""Entity names shared by the figure captions and plot tables in Analysis/.

The drawing rules (fonts, colours, sizes, export) live in Analysis/matlab/fig_style.m;
MATLAB draws every committed data figure. Nothing here touches a computed value.
"""

# Survivable-set design packages and failure classes, as named in captions.
ACTION_NAME = {'realloc_only': 'Thrust reallocation only',
               'mechanism': 'Guard mechanism',
               'parachute': 'Parachute-like device'}
FAILURE_NAME = {'one_out': 'One rotor out',
                'partial_authority': 'Partial authority (60%)',
                'two_adjacent': 'Two adjacent rotors out',
                'two_opposite': 'Two opposite rotors out'}
