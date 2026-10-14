import cmath
import json
import sys
from flask import Blueprint, render_template, jsonify, current_app
import numpy as np
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.fields import SubmitField, IntegerField
from wtforms.validators import InputRequired, NumberRange
from svgpathtools import Document

MAX_CIRCLES = 1000
MAX_CANVAS_SIZE = 10000
# Gap (in canvas pixels) kept between the drawing and the canvas edges.
CANVAS_MARGIN = 20
# Points sampled along each path. The FFT needs more than 2 * number_of_circles of them;
# extra samples make the coefficients more accurate.
MIN_SAMPLES = 1024
SAMPLES_PER_CIRCLE = 8

fourier_blueprint = Blueprint('fourier', __name__)

class FourierForm(FlaskForm):
    svg_file = FileField(u"SVG to plot", validators=[
        FileRequired(),
        FileAllowed(['svg'], 'svgs only!')
    ])
    canvas_width = IntegerField(u"The canvas width to plot on",
                                validators=[InputRequired(), NumberRange(1, MAX_CANVAS_SIZE)])
    canvas_height = IntegerField(u"The canvas height to plot on",
                                 validators=[InputRequired(), NumberRange(1, MAX_CANVAS_SIZE)])
    number_of_circles = IntegerField(u"How many circles to draw",
                                     validators=[InputRequired(), NumberRange(1, MAX_CIRCLES)])
    submit = SubmitField("Plot")


@fourier_blueprint.route("/")
def fourier_index():
    return render_template('fourier.html', form=FourierForm())


@fourier_blueprint.route('/fourier/get_constants', methods=['PUT', 'POST'])
def get_fourier_constants_post():
    form = FourierForm()
    if not form.validate_on_submit():
        return jsonify(errors=form.errors), 400

    f = form.svg_file.data
    try:
        paths = Document(f).paths()
    except Exception:
        # Malformed XML, path data or shape attributes surface as assorted exception types.
        current_app.logger.info('Could not read %s', f.filename, exc_info=True)
        return jsonify(errors={'svg_file': ['Could not read this SVG file.']}), 400

    number_of_circles = form.number_of_circles.data
    current_app.logger.debug('Calculating fourier constants for %s with %d circles', f.filename, number_of_circles)
    fourier_constants = calculate_fourier_for_paths(paths, number_of_circles,
                                                    form.canvas_width.data, form.canvas_height.data)
    if not fourier_constants:
        return jsonify(errors={'svg_file': ['This SVG contains nothing to draw.']}), 400
    return jsonify(convert_fourier_constants_for_js(fourier_constants))


def convert_fourier_constants_for_js(constants):
    result = []
    for constant in constants:
        result.append(convert_fourier_constant_for_js(constant))
    return result


def convert_fourier_constant_for_js(constant):
    radius, angle = cmath.polar(constant['C'])
    return {
        's': constant['speed'],
        'r': radius,
        'a': angle
    }


def sample_path(path, num_samples):
    """Samples `path` at the `num_samples` parameter values t = k / num_samples.

    Each segment gets a whole number of samples, roughly in proportion to its length.
    Where the path jumps (between subpaths, and from its end back to its start), the
    sample on the jump is the midpoint of both sides. This makes the FFT of the samples
    a trapezoidal-rule estimate of the Fourier coefficients that stays accurate across jumps.
    """
    lengths = np.array([segment.length() for segment in path])
    first = np.rint(np.cumsum(np.concatenate(([0], lengths))) / lengths.sum() * num_samples).astype(int)
    samples = np.empty(num_samples, dtype=complex)
    previous_end = path.end
    for segment, start, end in zip(path, first[:-1], first[1:]):
        if start == end:
            continue
        samples[start:end] = segment.point(np.arange(end - start) / (end - start))
        samples[start] = (previous_end + segment.start) / 2
        previous_end = segment.end
    return samples


def fit_to_canvas(bbox, canvas_width, canvas_height):
    """Returns (scale, offset) such that `z * scale + offset` maps `bbox` (xmin, xmax, ymin, ymax)
    into the canvas, centred and keeping the aspect ratio."""
    xmin, xmax, ymin, ymax = bbox
    available_width = max(canvas_width - 2 * CANVAS_MARGIN, 1)
    available_height = max(canvas_height - 2 * CANVAS_MARGIN, 1)
    scales = []
    if xmax > xmin:
        scales.append(available_width / (xmax - xmin))
    if ymax > ymin:
        scales.append(available_height / (ymax - ymin))
    scale = min(scales) if scales else 1
    offset = ((canvas_width - (xmax - xmin) * scale) / 2 - xmin * scale
              + ((canvas_height - (ymax - ymin) * scale) / 2 - ymin * scale) * 1j)
    return scale, offset


def calculate_fourier_for_paths(paths, count, canvas_width, canvas_height):
    """Returns, for each path, the coefficients c_0, c_1, c_-1, ..., c_(count-1), c_-(count-1) of

        c_n = integral over t in [0, 1] of path(t) * exp(-2*pi*i*n*t) dt

    with all paths scaled and positioned together to fit a canvas_width x canvas_height canvas.
    """
    paths = [path for path in paths if len(path) > 0 and path.length() > 0]
    if not paths:
        return []
    num_samples = max(MIN_SAMPLES, SAMPLES_PER_CIRCLE * count)
    speeds = [0] + [speed for n in range(1, count) for speed in (n, -n)]
    coefficients = []
    bboxes = []
    for path in paths:
        samples = sample_path(path, num_samples)
        coefficients.append(np.fft.fft(samples)[speeds] / num_samples)
        bboxes.append((samples.real.min(), samples.real.max(), samples.imag.min(), samples.imag.max()))

    xmins, xmaxs, ymins, ymaxs = zip(*bboxes)
    scale, offset = fit_to_canvas((min(xmins), max(xmaxs), min(ymins), max(ymaxs)), canvas_width, canvas_height)
    result = []
    for path_coefficients in coefficients:
        # Mapping every point z to z * scale + offset scales all coefficients; only c_0 also moves.
        path_coefficients = path_coefficients * scale
        path_coefficients[0] += offset
        result.extend({'speed': speed, 'C': c} for speed, c in zip(speeds, path_coefficients))
    return result


if __name__ == "__main__":
    print(json.dumps(convert_fourier_constants_for_js(
        calculate_fourier_for_paths(Document(sys.argv[1]).paths(), int(sys.argv[2]), 600, 600))))
