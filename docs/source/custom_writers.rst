==============
Custom writers
==============

The output formats of ``ECGTable.write_ecg`` are pluggable: next to the
built-in writers, you can supply any ``BaseWriter`` subclass through the
``writer`` argument, either as a class or as a configured instance.
When passed as a class, the writer is instantiated without arguments, so every
constructor parameter must carry a default.
This page describes what a custom writer needs to do, walks through a worked example,
and introduces the ``WriterValidator`` pre-flight check.

Requirements checklist
----------------------

To create a working writer, your ``BaseWriter`` subclass must implement the
``write`` method. The class may optionally override three filename-related
attributes/methods, and may optionally override ``reset`` to clear state
your writer keeps between the chunks of one run (see
`Resetting per-run state`_ below); neither override is required.
The ``WriteContext`` (i.e. ``ctx``, see `The WriteContext`_ below for
the full field list) provides runtime information and is internally
passed to ``write`` by ``ECGTable``. 
You therefore do not need to touch this yourself, it is simply available to 
source information to the ``Writer`` callable.

The ``write`` method needs to write one or more files to disk and can 
use the ``file_names`` and ``file_ext`` methods along with the ``ctx.target`` 
and ``ctx`` Booleans ``e_meta``, ``e_wave``, ``e_median`` to wire the indented 
file output and location. 

Depending on the type of writer, it can be important to include 
options for error handling using ``ctx.skip_data`` and ``ctx.failed_records``.
This might be especially important if you are applying additional processing
steps beyond simple writing to disk.
For example if you want to create a figure from the signal data,
or if you are performing chunk based processes which cannot be conducted
using the record specific engineering callables. 

The ``WriterValidator`` class include a ``describe`` method which 
lists the current requirements and WriteContext fields available
for a user. 

.. doctest::

    >>> from ecgprocess.writer import WriterValidator
    >>> WriterValidator.describe()  # doctest: +NORMALIZE_WHITESPACE
    BaseWriter contract checklist:
    <BLANKLINE>
    Required method:
      write(meta_list, wave_list, median_list, ctx) – process and
        write data to disk using ctx.target as output directory.
        Should respect ctx.e_meta, ctx.e_wave, ctx.e_median flags to
        conditionally write each data type. On write failure, append
        (record_id, error_reason) to ctx.failed_records,
        and skip the record if ctx.skip_data is True.
    <BLANKLINE>
    Optional overrides (have sensible defaults):
      FILE_EXT – class attribute (str) for file extension including
        dot (e.g. '.json'). Default ''. Used by file_names().
      file_ext() – return FILE_EXT or a runtime-computed extension
        (e.g. with compression suffix). Called by file_names().
      file_names(chunk_num=None) – return a tuple of at least one
        filename string. Base implementation returns the standard
        5-tuple (metadata, waveforms, medianbeats, ecg_data, figures);
        derive names from FileNames constants + file_ext() + optional
        chunk suffix. Use only the slots relevant to your format and
        ignore the rest.
    <BLANKLINE>
    WriteContext fields (passed to write()):
      All fields are populated internally by ECGTable.
    <BLANKLINE>
      Required (no default):
        e_meta (bool) – include metadata in output
        e_wave (bool) – include waveform signals in output
        e_median (bool) – include median beat signals in output
        key_list (list) – per-record unique identifiers (ECGTable's
          index); may be used as row keys in outputs
        target (str) – output directory path; write files here
        chunk_num (int or None) – current chunk number (or None for
          single-chunk runs); passed to file_names() for naming
      Optional (have defaults):
        skip_data (bool, default False) – if True, skip records
          that fail during write; if False, raise on failure
        failed_records (list, default []) – shared mutable list of
          (record_id, error_reason) tuples; append failures here,
          never reassign the list or ECGTable won't see them
    <BLANKLINE>

See also
~~~~~~~~

- :doc:`../examples/recipe/writer` — worked example of a custom writer,
  including validation

The write method
--------------------

A writer implements a single required method:

.. code-block:: python

    def write(self, meta_list, wave_list, median_list, ctx):
        ...

For every chunk of processed files, ``ECGTable.write_ecg`` calls
`write` once with four arguments:

* ``meta_list`` — a list of per-record metadata dictionaries;
* ``wave_list`` — a list of per-record waveform dictionaries, mapping
  lead names to ``numpy`` arrays (an absent lead maps to ``None``);
* ``median_list`` — the same structure for the median beat signals;
* ``ctx`` — a ``WriteContext`` carrying the export flags, the target
  directory, and the per-record keys.

The three lists are index-aligned: position ``i`` in each list belongs
to the record with key ``ctx.key_list[i]``.

A compliant ``write``:

* honours the export flags — only writes metadata when ``ctx.e_meta``
  is set, waveforms when ``ctx.e_wave``, and median beats when
  `ctx.e_median`;
* writes all files into the ``ctx.target`` directory;
* derives its filenames through ``self.file_names`` so chunked runs
  (`ctx.chunk_num`) receive the standard ``_N`` suffix.

The WriteContext
--------------------

The context object carries the state a writer needs, decoupling it
from ``ECGTable``.
ECGTable builds the ``WriteContext`` object and passes it to your ``write`` method.
The parsed ``WriteContext`` instances contains the following fields which 
can be used by the writer during runtime. 

``e_meta``, ``e_wave``, ``e_median`` : ``bool``
    Whether metadata, waveform, and median beat data should be
    exported. Data for a disabled source may still be passed; a
    compliant writer ignores it.
``key_list`` : ``list``
    The per-record unique keys, index-aligned with the three data
    lists; typically used as identifiers in the output.
``target`` : ``str``
    The directory all output files are written to.
``chunk_num`` : ``int`` or ``None``
    The current chunk number when writing separate files per chunk,
    or ``None`` for a single-file run. Forward it to ``file_names``
    rather than formatting filenames manually.
``skip_data`` : ``bool``, default ``False``
    Whether a record failing at the write stage should be skipped and
    recorded instead of raising; mirrors the ``ECGTable``
    ``ignore_data`` flag. See `Failure policy`_.
``failed_records`` : ``list`` [``tuple`` [``str``, ``str``]], default ``[]``
    The (identifier, cause) pairs of records skipped at the write
    stage; merged into ``FailedFiles.txt`` by ``write_ecg``. Append
    failures here; never reassign the list or ``ECGTable`` won't see them.

Filename conventions
--------------------

Writers own their filenames through three pieces of shared machinery
on ``BaseWriter``:

* ``FILE_EXT`` — a class attribute holding the on-disk extension,
  including the leading dot (e.g. ``'.json'``). Writers that name
  their own files keep the empty default.
* ``file_ext()`` — returns ``FILE_EXT`` by default; override it when
  the extension depends on an option (e.g. a compression suffix).
* ``file_names(chunk_num=None)`` — returns a tuple of at least one
  filename. The base implementation returns the five standard filenames
  (metadata, waveforms, medianbeats, ecg_data, figures) with the chunk
  suffix and extension applied. Use only the slots relevant to your
  format and ignore the rest.

A writer that names its own files (such as the per-record image
writer) may bypass ``file_names`` entirely, or override it to return
a custom set of filenames. ``WriterValidator`` checks that the method
returns a tuple of at least one filename string.

Resetting per-run state
------------------------

The ``reset`` method is implemented to allow a writer instance to be 
passed to more than one ``ECGTable.write_ecg`` call. 
The default ``reset()`` in ``BaseWriter`` does nothing. 
A writer with a per-run state, for example where a file header
is included with the first chunk, can re-define the method
in the writer code to make sure the state results each time a new
write_ecg call is made.

Failure policy
--------------

Errors caused by invalid writer configuration (e.g., unsupported options)
should be raised immediately.
For per-record data failures, honour ``ctx.skip_data``:
when it is set, append ``(identifier, cause)`` to
``ctx.failed_records`` and continue with the remaining records —
``write_ecg`` merges the pairs into ``FailedFiles.txt``; when it is
not set, raise an ``InputValidationError`` naming the record.

Worked example: a JSON writer
-----------------------------

The following writer bundles each chunk into a single ``.json`` file
using only the standard library:

.. code-block:: python

    import json
    import os
    from ecgprocess.writer import BaseWriter
    
    class JsonWriter(BaseWriter):
        """Writes each chunk of extracted ECG data to one .json."""
        FILE_EXT = '.json'
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        def write(self, meta_list, wave_list, median_list, ctx):
            # the fourth standard name is the bundled-output slot
            # writing to a single file so using `ecg_file` here.
            _, _, _, ecg_file, _ = self.file_names(
                chunk_num=ctx.chunk_num)
            record = {'identifiers': list(ctx.key_list)}
            if ctx.e_meta:
                record['metadata'] = meta_list
            if ctx.e_wave:
                record['waveforms'] = self._signals(wave_list)
            if ctx.e_median:
                record['medianbeats'] = self._signals(median_list)
            with open(os.path.join(ctx.target, ecg_file), 'w') as fh:
                json.dump(record, fh)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        @staticmethod
        def _signals(signal_list):
            """Map numpy arrays to lists, dropping absent leads."""
            return [
                {lead: signal.tolist()
                 for lead, signal in signals.items()
                 if signal is not None}
                for signals in signal_list
            ]

Validating your writer
----------------------

Use ``WriterValidator`` to check a ``BaseWriter`` subclass before running a batch —
a quick, data-free pre-flight that never writes files. Note that ``WriterValidator``
only validates ``BaseWriter`` subclasses; bare function writers cannot be validated
this way (see `Limitations`_).

.. code-block:: python

    from ecgprocess.writer import WriterValidator
    WriterValidator(JsonWriter)   # passes silently if all is well

Any problems are collected and raised in a single error, so you see
everything at once:

.. code-block:: text

    the supplied writer failed validation with 2 violation(s):
    - a non-empty `FILE_EXT` must start with a dot; got `json`.
    - `file_names()` must return 5 filenames, got 3.

``WriterValidator`` checks: that you've subclassed ``BaseWriter``, implemented
the abstract ``write`` method, that ``write`` accepts the four data arguments
(extra defaulted parameters are OK), that a class can be instantiated with
no arguments, and that the filename machinery works.

Using WriterValidator.describe()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Call `WriterValidator.describe()` to print a human-readable checklist of
what your writer must do:

.. code-block:: python

    from ecgprocess.writer import WriterValidator
    WriterValidator.describe()

This outputs the exact requirements for ``write``, optional overrides,
and ``WriteContext`` fields — all embedded in the `Requirements checklist`_
section above.

.. _Limitations:

Limitations
~~~~~~~~~~~

`WriterValidator` does **not** check:

- that your ``write`` method actually writes files (it never calls ``write``);
- that your implementation handles missing leads correctly;
- that metadata/signal shapes match your output format;
- edge cases like empty chunks or per-record failures.

It's a shape check, not a behavior check. Test your writer with real data
before deploying it.

Notes
-----

* ``dataclass``-based writers must give every field a default to be
  usable via ``writer=MyWriter``; otherwise pass a configured
  instance.
* Writers defining ``__slots__`` should override ``__repr__``: the
  inherited representation reads ``vars(self)``, which slotted classes
  do not provide.
