"""
Define the Figure class that handles all plotting.
"""
import os
import sys
import subprocess
import webbrowser
from tempfile import NamedTemporaryFile, TemporaryDirectory
import base64

try:
    from IPython.display import Image
except ImportError:
    Image = None

from .clib import LibGMT
from .base_plotting import BasePlotting
from .utils import build_arg_string
from .decorators import fmt_docstring, use_alias, kwargs_to_strings


def figure(name):
    """
    Start a new figure.

    All plotting commands run afterward will append to this figure.

    Unlike the command-line version (``gmt figure``), this function does not
    trigger the generation of a figure file. An explicit call to
    :func:`gmt.savefig` or :func:`gmt.psconvert` must be made in order to get a
    file.

    Parameters
    ----------
    name : str
        A unique name for this figure. Will use the name to refer to a
        particular figure. You can come back to the figure by calling this
        function with the same name as before.

    """
    # Passing format '-' tells gmt.end to not produce any files.
    fmt = '-'
    with LibGMT() as lib:
        lib.call_module('figure', '{} {}'.format(name, fmt))


def unique_name():
    """
    Generate a unique name for a figure.

    Need a unique name for each figure, otherwise GMT will plot everything
    on the same figure instead of creating a new one.

    Returns
    -------
    name : str
        A unique name generated by ``tempfile.NamedTemporaryFile``

    """
    # Use the tempfile module to generate a unique file name.
    tmpfile = NamedTemporaryFile(prefix='gmt-python-', dir=os.path.curdir,
                                 delete=True)
    name = os.path.split(tmpfile.name)[-1]
    tmpfile.close()
    return name


def launch_external_viewer(fname):
    """
    Open a file in an external viewer program.

    Uses the ``xdg-open`` command on Linux, the ``open`` command on OSX, and
    the default web browser on other systems.

    Parameters
    ----------
    fname : str
        The file name of the file (preferably a full path).

    """
    # Redirect stdout and stderr to devnull so that the terminal isn't filled
    # with noise
    run_args = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Open the file with the default viewer.
    # Fall back to the browser if can't recognize the operating system.
    if sys.platform.startswith('linux'):
        subprocess.run(['xdg-open', fname], **run_args)
    elif sys.platform == 'darwin':  # Darwin is OSX
        subprocess.run(['open', fname], **run_args)
    else:
        webbrowser.open_new_tab('file://{}'.format(fname))


class Figure(BasePlotting):
    """
    A GMT figure to handle all plotting.

    Use the plotting methods of this class to add elements to the figure.  You
    can preview the figure using :meth:`gmt.Figure.show` and save the figure to
    a file using :meth:`gmt.Figure.savefig`.

    Unlike traditional GMT figures, no figure file is generated until you call
    :meth:`gmt.Figure.savefig` or :meth:`gmt.Figure.psconvert`.

    Examples
    --------

    >>> fig = Figure()
    >>> fig.psbasemap(region=[0, 360, -90, 90], projection='W7i', frame=True,
    ...               portrait=True)
    >>> fig.savefig("my-figure.png")
    >>> # Make sure the figure file is generated and clean it up
    >>> import os
    >>> os.path.exists('my-figure.png')
    True
    >>> os.remove('my-figure.png')

    """

    def __init__(self):
        self._name = unique_name()
        self._preview_dir = TemporaryDirectory(prefix=self._name + '-preview-')

    def __del__(self):
        # Clean up the temporary directory that stores the previews
        if hasattr(self, '_preview_dir'):
            self._preview_dir.cleanup()

    def _preprocess(self, **kwargs):
        """
        Call the ``figure`` module before each plotting command to ensure we're
        plotting to this particular figure.
        """
        figure(self._name)
        return kwargs

    @fmt_docstring
    @use_alias(F='prefix', T='fmt', A='crop', E='dpi', P='portrait')
    @kwargs_to_strings()
    def psconvert(self, **kwargs):
        """
        Convert [E]PS file(s) to other formats.

        Converts one or more PostScript files to other formats (BMP, EPS, JPEG,
        PDF, PNG, PPM, SVG, TIFF) using GhostScript.

        If no input files are given, will convert the current active figure
        (see :func:`gmt.figure`). In this case, an output name must be given
        using parameter *F*.

        {gmt_module_docs}

        {aliases}

        Parameters
        ----------
        A : str or bool
            Adjust the BoundingBox and HiResBoundingBox to the minimum required
            by the image content. Append ``u`` to first remove any GMT-produced
            time-stamps. Default is True.
        C : str
            Specify a single, custom option that will be passed on to
            GhostScript as is.
        E : int
            Set raster resolution in dpi. Default = 720 for PDF, 300 for
            others.
        F : str
            Force the output file name. By default output names are constructed
            using the input names as base, which are appended with an
            appropriate extension. Use this option to provide a different name,
            but without extension. Extension is still determined automatically.
        I : bool
            Enforce gray-shades by using ICC profiles.
        P : bool
            Force Portrait mode. All Landscape mode plots will be rotated back
            so that they show unrotated in Portrait mode. This is practical
            when converting to image formats or preparing EPS or PDF plots for
            inclusion in documents. Default to True.
        Q : str
            Set the anti-aliasing options for graphics or text. Append the size
            of the subsample box (1, 2, or 4) [4]. Default is no anti-aliasing
            (same as bits = 1).
        T : str
            Sets the output format, where b means BMP, e means EPS, E means EPS
            with PageSize command, f means PDF, F means multi-page PDF, j means
            JPEG, g means PNG, G means transparent PNG (untouched regions are
            transparent), m means PPM, s means SVG, and t means TIFF [default
            is JPEG]. To bjgt you can append - in order to get a grayscale
            image. The EPS format can be combined with any of the other
            formats. For example, ``'ef'`` creates both an EPS and a PDF file.
            The ``'F'`` creates a multi-page PDF file from the list of input PS
            or PDF files. It requires the *F* option.

        """
        kwargs = self._preprocess(**kwargs)
        # Default cropping the figure to True
        if 'A' not in kwargs:
            kwargs['A'] = ''
        # Default portrait mode to True
        if 'P' not in kwargs:
            kwargs['P'] = ''
        with LibGMT() as lib:
            lib.call_module('psconvert', build_arg_string(kwargs))

    def savefig(self, fname, orientation='portrait', transparent=False,
                crop=True, **kwargs):
        """
        Save the figure to a file.

        This method implements a matplotlib-like interface for
        :meth:`~gmt.Figure.psconvert`.

        Supported formats: PNG (``.png``), JPEG (``.jpg``), PDF (``.pdf``),
        BMP (``.bmp``), TIFF (``.tif``), and EPS (``.eps``).

        You can pass in any keyword arguments that
        :meth:`~gmt.Figure.psconvert` accepts.

        Parameters
        ----------
        fname : str
            The desired figure file name, including the extension. See the list
            of supported formats and their extensions above.
        orientation : str
            Either ``'portrait'`` or ``'landscape'``.
        transparent : bool
            If True, will use a transparent background for the figure. Only
            valid for PNG format.
        crop : bool
            If True, will crop the figure canvas (page) to the plot area.

        """
        # All supported formats
        fmts = dict(png='g', pdf='f', jpg='j', bmp='b', eps='e', tif='t')

        assert orientation in ['portrait', 'landscape'], \
            "Invalid orientation '{}'.".format(orientation)
        portrait = bool(orientation == 'portrait')

        prefix, ext = os.path.splitext(fname)
        ext = ext[1:]  # Remove the .
        assert ext in fmts, "Unknown extension '.{}'".format(ext)
        fmt = fmts[ext]
        if transparent:
            assert ext == 'png', \
                "Transparency unavailable for '{}', only for png.".format(ext)
            fmt = fmt.upper()

        self.psconvert(prefix=prefix, fmt=fmt, crop=crop,
                       portrait=portrait, **kwargs)

    def show(self, dpi=300, width=500, external=False):
        """
        Display a preview of the figure.

        Inserts the preview as a PNG on the Jupyter notebook.
        If ``external=True``, makes PDF preview instead and opens it in the
        default viewer for your operating system (falls back to the default
        web browser).

        If ``external=False``, you will need to have IPython installed for this
        to work.  You should have it if you are using a Jupyter notebook.

        Note that the external viewer does not block the current process.

        All previews are deleted when the current Python process is terminated.

        Parameters
        ----------
        dpi : int
            The image resolution (dots per inch).
        width : int
            Width of the figure shown in the notebook in pixels. Ignored if
            ``external=True``.
        external : bool
            View the preview as a PDF in an external viewer.

        Returns
        -------
        img : IPython.display.Image
            Only if ``external=False``.

        """
        if external:
            pdf = self._preview(fmt='pdf', dpi=600, anti_alias=False,
                                as_bytes=False)
            launch_external_viewer(pdf)
        else:
            png = self._preview(fmt='png', dpi=dpi, anti_alias=True,
                                as_bytes=True)
            img = Image(data=png, width=width)
            return img

    def _preview(self, fmt, dpi, anti_alias, as_bytes=False):
        """
        Grab a preview of the figure.

        Parameters
        ----------
        fmt : str
            The image format. Can be any extension that
            :meth:`~gmt.Figure.savefig` recognizes.
        dpi : int
            The image resolution (dots per inch).
        anti_alias : bool
            If True, will apply anti-aliasing to the image (using options
            ``Qg=4, Qt=4``).
        as_bytes : bool
            If ``True``, will load the image as a bytes string and return that
            instead of the file name.

        Returns
        -------
        preview : str or bytes
            If ``as_bytes=False``, this is the file name of the preview image
            file. Else, it is the file content loaded as a bytes string.

        """
        savefig_args = dict(dpi=dpi)
        if anti_alias:
            savefig_args['Qg'] = 4
            savefig_args['Qt'] = 4
        fname = os.path.join(self._preview_dir.name,
                             '{}.{}'.format(self._name, fmt))
        self.savefig(fname, **savefig_args)
        if as_bytes:
            with open(fname, 'rb') as image:
                preview = image.read()
            return preview
        return fname

    def _repr_png_(self):
        """
        Show a PNG preview if the object is returned in an interactive shell.
        For the Jupyter notebook or IPython Qt console.
        """
        png = self._preview(fmt='png', dpi=70, anti_alias=True, as_bytes=True)
        return png

    def _repr_html_(self):
        """
        Show the PNG image embedded in HTML with a controlled width.
        Looks better than the raw PNG.
        """
        raw_png = self._preview(fmt='png', dpi=300, anti_alias=True,
                                as_bytes=True)
        base64_png = base64.encodebytes(raw_png)
        html = '<img src="data:image/png;base64,{image}" width="{width}px">'
        return html.format(image=base64_png.decode('utf-8'), width=500)
