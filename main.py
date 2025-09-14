# AUTHOR Adam Gruca

import settings as sett

from qgis.core import QgsVectorLayer, QgsGeometry, QgsWkbTypes, QgsFeature
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

# NOT USED FOR NOW, MAY BE DELETED IN LATER COMMITS
# def unique_values_from_field(layer: QgsVectorLayer, field_name: str):
#     """
#     Returns unique values of a field as a set.
#     :param layer:
#     :param field_name:
#     :return:
#     """
#     assert field_name in [f.name() for f in layer.fields()], f'No field named "{field_name}" in layer'
#     idx = layer.fields().indexOf(field_name)
#     unique_values = layer.uniqueValues(idx)
#     return unique_values


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


def intersecting_points_sorted_by_direction(points_layer: QgsVectorLayer, line: QgsGeometry) -> list[QgsFeature]:
    """
    Searches for points intersecting with given line, and sorts them by distance from line start.
    :param points_layer:
    :param line:
    :return:
    """
    assert QgsWkbTypes.geometryType(line.wkbType()) == QgsWkbTypes.LineGeometry, f'Line is not LineGeometry'
    assert points_layer.geometryType() == QgsWkbTypes.PointGeometry, f'Points layer is not PointsGeometry'

    intersecting_points = {}  # {distance_along_line: point_object}
    for point in points_layer.getFeatures():
        if line.distance(point.geometry()) < 1e-6:
            intersecting_points[line.lineLocatePoint(point.geometry())] = point

    sorted_intersecting_points = [point for distance, point in
                                  dict(sorted(intersecting_points.items(), key=lambda item: item[0])).items()]

    return sorted_intersecting_points


def points_by_watercourse(points_layer: QgsVectorLayer, lines: dict[str, QgsGeometry]) -> dict[str, list[QgsFeature]]:
    """
    Intersects points by watercourse and sorts them by distance from the line starting point.
    :param points_layer:
    :param lines:
    :return:
    """
    assert points_layer.geometryType() == QgsWkbTypes.PointGeometry, f'Points layer is not PointsGeometry'

    sorted_points_by_watercourse = {}  # water_name: list_of_points_sorted_by_distance
    for name, line in lines.items():
        sorted_p = intersecting_points_sorted_by_direction(points_layer, line)
        sorted_points_by_watercourse[name] = sorted_p

    return sorted_points_by_watercourse


class PointsSegment:
    def __init__(self, start: int, end: int, char_start: str, char_end: str):
        self.start= start
        self.end = end
        self.char_start = char_start
        self.char_end = char_end
        self.fids = []

    def populate(self, points: list[QgsFeature]):
        self.fids = [f.id() for f in points[self.start: self.end]]



def segment_points_by_old_num(dict_of_points: dict[str, list[QgsFeature]], field_name: str):
    def calc_breakpoints(points: list[QgsFeature]) -> dict[int, str]:
        """
        If old number exists, get index of that point as a breakpoint
        :param points:
        :return:
        """
        breakpoints_dict: dict[int, str] = {}  # index_of_point, old_number
        for index, point in enumerate(points):
            try:
                old_num = point[field_name]
            except KeyError:
                print(f'Point don`t have field named "{field_name}"')
                exit()
            if old_num:
                breakpoints_dict[index] = old_num
        return breakpoints_dict

    def calc_intervals(breakpoints_dict: dict[int, str], points: list[QgsFeature]):
        """
        If any breakpoint exists, segment points by breakpoints.
        :param breakpoints_dict:
        :param points:
        :return:
        """
        indexes = sorted(breakpoints_dict.keys())
        segments = [[indexes[i] + 1, indexes[i + 1]] for i in range(len(indexes) - 1)]

        if indexes[0] == 0 and not segments:
            segments.append([1, len(points) + 1])
        if indexes[0] != 0 and not segments:
            segments.append([0, indexes[0]])
        if segments[-1][1] < len(points) - 1:
            segments.append([segments[-1][1] + 1, len(points) + 1])
        if segments[0][0] not in [0, 1]:
            segments.append([0, segments[0][0]])

        return segments

    # Main body of function, after subfunctions definition.
    list_of_segments: list[PointsSegment] = []
    for name, sorted_points in dict_of_points.items():
        if not sorted_points:
            continue

        breakpoints = calc_breakpoints(sorted_points)
        if not breakpoints:
            segments_by_breakpoints = [[0, len(sorted_points) + 1]]
        else:
            segments_by_breakpoints = calc_intervals(breakpoints, sorted_points)

        for segment in segments_by_breakpoints:
            start_char = breakpoints.get(segment[0], '')
            end_char = breakpoints.get(segment[1], '')
            segmented_points = PointsSegment(start=segment[0], end=segment[1],
                                                  char_start=start_char, char_end=end_char)
            segmented_points.populate(sorted_points)
            list_of_segments.append(segmented_points)
    return list_of_segments

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
    new_names_dict = prepare_new_values_dict(points, sett.POINT_OLD_NAME_FIELD)  # FID: new_name

    """
    Watercourses are opened and merged into single lines by unique name in field sett.LINE_IDENTIFICATION_FIELD.
    """
    lines = open_spatial_layer(sett.RESULTS_FILENAME, sett.LINE_LAYER_NAME)
    lines_by_name = merge_lines_by_field_value(lines, sett.LINE_IDENTIFICATION_FIELD)  # water_name: QgsGeometry_obj

    """
    Each watercourse gets a list of points it is intersecting with.
    Points are sorted by the distance along the line from the starting point.
    
    The intersection is realised by checking the distance between line and point, with 1e-6 threshold.
    QgsGeometry.intersects() method gives unrealistic results due to float point rounding error.
    """

    sorted_points = points_by_watercourse(points, lines_by_name)
    segmented_points = segment_points_by_old_num(sorted_points, sett.POINT_OLD_NAME_FIELD)


if __name__ == '__main__':
    main()
