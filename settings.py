"""
Settings for script solving the recruitment task for EnviroSolutions Sp z o. o.
AUTHOR Adam Gruca (https://github.com/Trexerx/) (C) 2025

Requirements:
    - Python 3.12 from Qgis distribution.
    This script was created using python 3.12 from Qgis 3.44.2 from OSGeo4W installer,
    but should work for any Qgis version with python 3.10+
"""

DATA_FILENAME = 'spatial_layers.gpkg'
RESULTS_FILENAME = 'results.gpkg'

LINE_LAYER_NAME = 'cieki'
LINE_IDENTIFICATION_FIELD = 'oznaczenie'

POINT_LAYER_NAME = 'punkty'
POINT_OLD_NAME_FIELD = 'numer-stary'
POINT_NEW_NAME_FIELD = 'numer-nowy'

if __name__ == '__main__':
    print('Run solve_recruitment_task.py to start the script!')
