GLYPHS = {
    "a": ("111", "101", "111", "101", "101"),
    "n": ("1001", "1101", "1111", "1011", "1001"),
    "d": ("1110", "1011", "1001", "1011", "1110"),
    "r": ("1110", "1010", "1110", "1110", "1011"),
    "e": ("11", "10", "11", "10", "11"),
    "b": ("111", "101", "111", "101", "111"),
    "l": ("10", "10", "10", "10", "11"),
    "o": ("111", "101", "101", "101", "111"),
    ".": ("0", "0", "0", "0", "1"),
    "c": ("11", "10", "10", "10", "11"),
    "m": ("10001", "11011", "11111", "10101", "10101"),
}


def pixel_cells(content):
    cells = set()
    cursor = 0
    for character in content:
        glyph = GLYPHS[character]
        if len(glyph) != 5 or len({len(row) for row in glyph}) != 1:
            raise ValueError(f"Invalid glyph: {character}")
        for row, values in enumerate(glyph):
            for column, value in enumerate(values):
                if value == "1":
                    cells.add((cursor + column, 4 - row))
        cursor += len(glyph[0]) + 1
    width = cursor - 1
    for column in range(-1, width + 1):
        for row in range(-1, 6):
            corners = [(column, row), (column + 1, row), (column, row + 1), (column + 1, row + 1)]
            occupied = tuple(point in cells for point in corners)
            if occupied in ((True, False, False, True), (False, True, True, False)):
                raise ValueError("Diagonal-only pixel contact would create a non-manifold cutter")
    return cells, width


def engrave_pixel_brand(lid, target, builder, specification):
    cells, width = pixel_cells(specification["content"])
    pitch = specification["pixel_pitch"]
    lower_x = -width * pitch / 2
    lower_z = specification["center_z"] - 5 * pitch / 2
    back_y = builder["PARAMETERS"]["back_y"]
    depths = (back_y - specification["engraving_depth"], back_y + 0.5)
    vertices = []
    vertex_indices = {}
    faces = []

    def vertex_index(column, depth_index, row):
        key = (column, depth_index, row)
        if key not in vertex_indices:
            vertex_indices[key] = len(vertices)
            vertices.append((-(lower_x + column * pitch), depths[depth_index], lower_z + row * pitch))
        return vertex_indices[key]

    for column, row in sorted(cells):
        corners = [vertex_index(column + horizontal, depth, row + vertical) for vertical in (0, 1) for depth in (0, 1) for horizontal in (0, 1)]
        face_definitions = [((0, 1, 5, 4), True), ((2, 6, 7, 3), True), ((0, 2, 3, 1), (column, row - 1) not in cells), ((4, 5, 7, 6), (column, row + 1) not in cells), ((0, 4, 6, 2), (column - 1, row) not in cells), ((1, 3, 7, 5), (column + 1, row) not in cells)]
        for indices, include in face_definitions:
            if include:
                faces.append(tuple(corners[index] for index in indices))
    cutter = builder["mesh_object"]("CUT | robust pixel andreabalbo.com", vertices, faces, target)
    builder["clean_mesh"](cutter)
    cutter["content"] = specification["content"]
    cutter["display_style"] = "Uppercase-style rectilinear pixel glyphs; domain spelling unchanged"
    cutter["reading_direction"] = "Readable from the rear, viewed from positive Y"
    cutter["minimum_grid_feature_mm"] = pitch
    cutter["engraving_depth_mm"] = specification["engraving_depth"]
    builder["boolean"](lid, cutter)
    return cutter
