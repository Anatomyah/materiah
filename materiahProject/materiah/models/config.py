PHONE_PREFIX_CHOICES = [
    ('050', '050'),
    ('051', '051'),
    ('052', '052'),
    ('053', '053'),
    ('054', '054'),
    ('055', '055'),
    ('056', '056'),
    ('058', '058'),
    ('059', '059'),
    ('02', '02'),
    ('03', '03'),
    ('04', '04'),
    ('05', '05'),
    ('08', '08'),
    ('09', '09'),
    ('071', '071'),
    ('072', '072'),
    ('073', '073'),
    ('074', '074'),
    ('076', '076'),
    ('077', '077'),
    ('079', '079'),
]

"""
PHONE_PREFIX_CHOICES is a list of tuples used to define the available Israeli phone number prefixes in the system. 
Each tuple contains two identical strings, the first being the key and the second being the display value. 
These prefixes are used throughout the application to validate and categorize phone numbers based on their geographical
 or network-based origin.

- The first three digits typically represent the mobile network operator (e.g., '050', '051', '052' for Cellcom).
- The two-digit prefixes usually denote geographic regions (e.g., '02' for Jerusalem, '03' for Tel Aviv).
- Some prefixes also indicate fixed-line services from various telecom providers.

This list is utilized primarily in forms and model fields where phone numbers are input or displayed, ensuring that
 users select a valid prefix for their phone numbers.
"""
