# AUTHOR Adam Gruca

import settings as sett
from qgis.core import QgsVectorLayer, QgsGeometry, QgsWkbTypes
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


def unique_values_from_field(layer: QgsVectorLayer, field_name: str):
    """
    Returns unique values of a field as a set.
    :param layer:
    :param field_name:
    :return:
    """
    assert field_name in [f.name() for f in layer.fields()], f'No field named "{field_name}" in layer'
    idx = layer.fields().indexOf(field_name)
    unique_values = layer.uniqueValues(idx)
    return unique_values


def prepare_new_values_dict(layer: QgsVectorLayer, old_name_field: str) -> dict:
    """
    Maps old numbers to FIDs, no number -> 'NULL' value
    :param layer:
    :param old_name_field:
    :return:
    """
    assert old_name_field in [f.name() for f in layer.fields()], f'No field named "{old_name_field}" in layer'
    old_names_dict = {
        f.id(): f[old_name_field] if f[old_name_field] is not None else "NULL"
        for f in layer.getFeatures()
    }
    return old_names_dict


def merge_lines_by_field_value(layer: QgsVectorLayer, field_name: str) -> dict[str, QgsGeometry]:
    """
    Returns lines as QgsGeometry merged by unique field values
    :param layer:
    :param field_name:
    :return:
    """
    assert field_name in [f.name() for f in layer.fields()], f'No field named "{field_name}" in layer'
    assert layer.geometryType() == QgsWkbTypes.LineGeometry, f'Layer is not LineGeometry'

    multilines: dict[str, QgsGeometry] = {}

    for feat in layer.getFeatures():
        feat_name = feat[field_name]
        feat_geom = feat.geometry()

        if feat_name not in multilines:
            multilines[feat_name] = QgsGeometry(feat_geom)
        else:
            multilines[feat_name] = multilines[feat_name].combine(feat_geom)

    lines: dict[str, QgsGeometry] = {}
    for feat_name, multiline in multilines.items():
        lines[feat_name] = multiline.mergeLines()

    return lines



# ============================================================================================================ MAIN ===
def main():

    """
    In order to preserve original spatial data, the script creates a copy to work on
    """
    create_results_file(sett.DATA_FILENAME, sett.RESULTS_FILENAME)

    """
    The new_names dict is a temporary dictionary that stores all new names for points before assigning them into file.
    When it is created it contains only values from old field, or else, string 'NULL'. The 'NULL' string will be later
    replaced if the point is located on the watercourse, leaving the ones that don`t intersect with default 'NULL'.
    
    !!!
    I decided to make 'NULL' a string value because that was specified in the task description, it was described as
    value and followed styling convention of other strings. Otherwise I would just leave it with no values.
    """
    points = open_spatial_layer(sett.RESULTS_FILENAME, sett.POINT_LAYER_NAME)
    new_names_dict = prepare_new_values_dict(points, sett.POINT_OLD_NAME_FIELD)

    """
    Watercourses are opened and merged into single lines by unique name in field sett.LINE_IDENTIFICATION_FIELD.
    """
    lines = open_spatial_layer(sett.RESULTS_FILENAME, sett.LINE_LAYER_NAME)
    lines_by_name = merge_lines_by_field_value(lines, sett.LINE_IDENTIFICATION_FIELD)


if __name__ == '__main__':
    main()
