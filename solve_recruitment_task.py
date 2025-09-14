"""
Script solving the recruitment task for EnviroSolutions Sp z o. o.
AUTHOR Adam Gruca (https://github.com/Trexerx/)  (C) 2025

Requirements:
    - Python 3.12 from Qgis distribution.
    This script was created using python 3.12 from Qgis 3.44.2 from OSGeo4W installer,
    but should work for any Qgis version with python 3.10+
"""

import settings as sett

from qgis.core import QgsVectorLayer, QgsGeometry, QgsWkbTypes, QgsFeature
from pathlib import Path
from shutil import copy2
from string import ascii_lowercase


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
    Opens specified layer from geospatial file.
    :param filename:
    :param layer_name:
    :return:
    """
    uri = f"{filename}|layername={layer_name}"
    opened_layer = QgsVectorLayer(uri, layer_name, "ogr")
    assert opened_layer.isValid(), f"Cannot properly load layer {layer_name} from {filename}"
    return opened_layer


def prepare_new_values_dict(layer: QgsVectorLayer, old_name_field: str) -> dict[int, str]:
    """
    Maps old names to FIDs, no name -> 'NULL' value.
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
    Returns lines as QgsGeometry merged by unique field values.
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

    sorted_points_by_watercourse = {}  # line_name: list_of_points_sorted_by_distance
    for name, line in lines.items():
        sorted_p = intersecting_points_sorted_by_direction(points_layer, line)
        sorted_points_by_watercourse[name] = sorted_p

    return sorted_points_by_watercourse


class PointsSegment:
    def __init__(self, start: int, end: int, char_start: str, char_end: str):
        self.start = start
        self.end = end
        self.char_start = char_start
        self.char_end = char_end
        self.state = self._define_state()
        self.fids = []
        self.names = {}  # FID: new-name

    def __str__(self):
        return (f'PointsSegment(start=[{self.start}, {self.char_start}], end=[{self.end}, {self.char_end}],'
                f' count={len(self.fids)})')

    def populate(self, points: list[QgsFeature]):
        """
        Adds points` FIDs basing on start-end range.
        :param points:
        :return:
        """
        self.fids = [f.id() for f in points[self.start: self.end]]

    def _define_state(self) -> int:
        """
        1-no starting old name, no ending old name;
        2-no starting old name, ending old name exists;
        3-starting old name exists, ending old name exists;
        4-starting old name exists, no ending old name;
        :return:
        """
        if not self.char_start:
            if not self.char_end:
                return 1
            else:
                return 2
        else:
            if self.char_end:
                return 3
            else:
                return 4

    def create_new_names(self):
        """
        New names based on state.
        """
        if not self.fids:
            return
        match self.state:
            case 1:
                self._naming_one()
            case 2:
                self._naming_two()
            case 3:
                self._naming_three()
            case 4:
                self._naming_four()
            case _:
                return

    def _naming_one(self):
        """
        New names based on state 1-no starting old name, no ending old name.
        """
        self.names = {fid: f'{num+1}P' for num, fid in enumerate(self.fids)}

    def _naming_two(self):
        """
        New names based on state 2-no starting old name, ending old name exists.
        """
        self.names = {fid: f'{num+1}Pnowy' for num, fid in enumerate(self.fids)}

    def _naming_three(self):
        """
        New names based on state 3-starting old name exists, ending old name exists.
        """

        def _next_letter():
            """
            Next letter of alphabet generator, if called more times than letters it yields 'aa', 'ab' ... etc.
            """
            letters = ascii_lowercase
            n = 1
            while True:
                num = n
                result = ""
                while num > 0:
                    num, remainder = divmod(num - 1, 26)
                    result = letters[remainder] + result
                yield result
                n += 1

        letter = _next_letter()
        self.names = {fid: f'{self.char_start}{next(letter)}' for fid in self.fids}

    def _naming_four(self):
        """
        New names based on state 4-starting old name exists, no ending old name.
        :return:
        """
        start_number = int(self.char_start[:-1])
        self.names = {fid: f'{start_number+num+1}P' for num, fid in enumerate(self.fids)}


def segment_points_by_old_num(dict_of_points: dict[str, list[QgsFeature]], field_name: str):
    def calc_breakpoints(points: list[QgsFeature]) -> dict[int, str]:
        """
        If old name exists, get index of that point as a breakpoint.
        :param points:
        :return:
        """
        breakpoints_dict: dict[int, str] = {}  # index_of_point: old_name
        for index, point in enumerate(points):
            try:
                old_num = point[field_name]
            except KeyError:
                print(f'Point don`t have field named "{field_name}"')
                exit()
            if old_num:
                breakpoints_dict[index] = old_num
        return breakpoints_dict

    def calc_intervals(breakpoints_dict: dict[int, str], points_on_tle_line: list[QgsFeature]):
        """
        If any breakpoint exists, segment points by breakpoints.
        :param breakpoints_dict:
        :param points_on_tle_line:
        :return:
        """
        indexes = sorted(breakpoints_dict.keys())
        segments = [[indexes[i] + 1, indexes[i + 1]] for i in range(len(indexes) - 1)]

        if indexes[0] == 0 and not segments:
            segments.append([1, len(points_on_tle_line) + 1])
        if indexes[0] != 0 and not segments:
            segments.append([0, indexes[0]])
        if segments[-1][1] < len(points_on_tle_line) - 1:
            segments.append([segments[-1][1] + 1, len(points_on_tle_line) + 1])
        if segments[0][0] not in [0, 1]:
            segments.append([0, segments[0][0]-1])

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
            if segment[0] == 0:
                start_char = ''
            else:
                start_char = breakpoints.get(segment[0]-1, '')
            if segment[1] > len(sorted_points):
                end_char = ''
            else:
                end_char = breakpoints.get(segment[1], '')

            segmented_points = PointsSegment(start=segment[0], end=segment[1],
                                             char_start=start_char, char_end=end_char)
            segmented_points.populate(sorted_points)

            list_of_segments.append(segmented_points)
    return list_of_segments


def create_new_names(base_dict: dict[int, str], list_of_segments: list[PointsSegment]) -> dict[int, str]:
    """
    For each segment, update dict for storing new names.
    :param base_dict: dictionary mapping FID with new name, waiting for update
    :param list_of_segments:
    :return:
    """
    for segment in list_of_segments:
        segment.create_new_names()
        base_dict.update(segment.names)

    return base_dict


def assign_new_names(point_layer: QgsVectorLayer, fids_with_new_names: dict[int, str], new_name_field: str):
    """
    Assign new names by FID into a specified field, using PyQGIS .dataProvider().
    :param point_layer:
    :param fids_with_new_names:
    :param new_name_field:
    :return:
    """
    assert new_name_field in [f.name() for f in point_layer.fields()], f'No field named "{new_name_field}" in layer'

    field_index = point_layer.fields().indexOf(new_name_field)
    change_dict = {fid: {field_index: new_name} for fid, new_name in fids_with_new_names.items()}

    """
    Because GDAL is trying to read metadata of whole .gpkg file during changeAttributeValues(), it often results
    in an 'failed: unable to open database file' error. It have no influence on the proper work of this script, so
    printing is disabled for a brief moment of changing data. 
    """
    from osgeo.gdal import PushErrorHandler, PopErrorHandler
    PushErrorHandler('CPLQuietErrorHandler')
    point_layer.dataProvider().changeAttributeValues(change_dict)
    PopErrorHandler()


# =====***=====***=====***=====***=====***=====***=====***=====***=====***=====***=====***=====***=====*** MAIN =====***
def solve_recruitment_task():
    """
    Assign new names to points while meeting specific conditions.
    :return:
    """

    """
    In order to preserve original spatial data, the script creates a copy to work on.
    """
    create_results_file(sett.DATA_FILENAME, sett.RESULTS_FILENAME)

    """
    The new_names dict is a temporary dictionary that stores all new names for points before assigning them into file.
    When it is created it contains only values from old field, or else, string 'NULL'. The 'NULL' string will be later
    replaced if the point is located on the watercourse, leaving the ones that don`t intersect with default 'NULL'.
    """
    points = open_spatial_layer(sett.RESULTS_FILENAME, sett.POINT_LAYER_NAME)
    new_names_dict = prepare_new_values_dict(points, sett.POINT_OLD_NAME_FIELD)  # FID: new_name

    """
    Watercourses are opened and merged into single lines by unique name in field sett.LINE_IDENTIFICATION_FIELD.
    """
    lines = open_spatial_layer(sett.RESULTS_FILENAME, sett.LINE_LAYER_NAME)
    lines_by_name = merge_lines_by_field_value(lines, sett.LINE_IDENTIFICATION_FIELD)  # line_name: QgsGeometry_obj
    del lines

    """
    Each watercourse gets a list of points it is intersecting with.
    Points are sorted by the distance along the line from the starting point.
    Then, they are further segmented by breakpoints - points with old names.
    
    The intersection is realised by checking the distance between line and point, with 1e-6 threshold.
    QgsGeometry.intersects() method gives unrealistic results due to float point rounding error.
    """
    sorted_points = points_by_watercourse(points, lines_by_name)  # line_name: list_of_points_sorted_by_distance
    segmented_points = segment_points_by_old_num(sorted_points, sett.POINT_OLD_NAME_FIELD)

    """
    New names are being created. Then, the points layer is being updated and saved.
    """
    new_names_dict = create_new_names(new_names_dict, segmented_points)
    assign_new_names(points, new_names_dict, sett.POINT_NEW_NAME_FIELD)
    del points


if __name__ == '__main__':
    solve_recruitment_task()
