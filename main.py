# AUTHOR Adam Gruca

import settings as sett
from qgis.core import QgsVectorLayer
from pathlib import Path
from shutil import copy2


def create_results_file(old_filename: str | Path, new_filename: str | Path):
    """
    Copies data file to work on a new one.
    :param old_filename: source
    :param new_filename: destination
    :return:
    """
    copy2(old_filename, new_filename)
    assert Path(new_filename).exists(), 'Creating copy of spatial data failed'

def open_spatial_layer(filename: str | Path, layer_name: str) -> QgsVectorLayer:
    """
    Opens specified layer from geospatial file
    :param filename:
    :param layer_name:
    :return:
    """
    uri = f"{filename}|layername={layer_name}"
    opened_layer = QgsVectorLayer(uri, layer_name, "ogr")
    assert opened_layer.isValid(), f"Cannot properly load layer {layer_name} from {filename}"
    return opened_layer


# ============================================================================================================ MAIN ===
def main():

    """
    In order to preserve original spatial data, the script creates a copy to work on
    """
    create_results_file(sett.DATA_FILENAME, sett.RESULTS_FILENAME)

    points = open_spatial_layer(sett.RESULTS_FILENAME, sett.POINT_LAYER_NAME)
    lines = open_spatial_layer(sett.RESULTS_FILENAME, sett.LINE_LAYER_NAME)


if __name__ == '__main__':
    main()
