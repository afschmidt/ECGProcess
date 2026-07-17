==============
Custom writers
==============

The output formats of :meth:`~ecgprocess.tabular.ECGTable.write_ecg`
are pluggable: next to the built-in writers, any
:class:`~ecgprocess.writer.BaseWriter` subclass can be supplied through
the ``writer`` argument, either as a class or as a configured instance:

.. code-block:: python

    from ecgprocess.writer import BaseWriter, validate_writer

    ecgtable.write_ecg(writer=JsonWriter, target_path='out/')
    # or, when the writer takes constructor options
    ecgtable.write_ecg(writer=JsonWriter(indent=2), target_path='out/')

When passed as a class, the writer is instantiated without arguments,
so every constructor parameter must carry a default. This page
describes the contract a custom writer must honour, walks through a
worked example, and introduces the
:func:`~ecgprocess.writer.validate_writer` pre-flight check.

The ``write`` method
--------------------

A writer implements a single required method:

.. code-block:: python

    def write(self, meta_list, wave_list, median_list, ctx):
        ...

For every chunk of processed files, ``ECGTable.write_ecg`` calls
``write`` once with four arguments:

* ``meta_list`` — a list of per-record metadata dictionaries;
* ``wave_list`` — a list of per-record waveform dictionaries, mapping
  lead names to ``numpy`` arrays (an absent lead maps to ``None``);
* ``median_list`` — the same structure for the median beat signals;
* ``ctx`` — a :class:`~ecgprocess.writer.WriteContext` carrying the
  export flags, the target directory, and the per-record keys.

The three lists are index-aligned: position ``i`` in each list belongs
to the record with key ``ctx.key_list[i]``. A compliant ``write``:

* honours the export flags — only writes metadata when ``ctx.e_meta``
  is set, waveforms when ``ctx.e_wave``, and median beats when
  ``ctx.e_median``;
* writes all files into the ``ctx.target`` directory;
* derives its filenames through ``self.file_names`` so chunked runs
  (``ctx.chunk_num``) receive the standard ``_N`` suffix.

The ``WriteContext``
--------------------

The context object carries the state a writer needs, decoupling it
from ``ECGTable``:

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
``skip_data`` : ``bool``
    Whether a record failing at the write stage should be skipped and
    recorded instead of raising; mirrors the ``ECGTable``
    ``ignore_data`` flag. See `Failure policy`_.
``failed_records`` : ``list`` [``tuple`` [``str``, ``str``]]
    The (identifier, cause) pairs of records skipped at the write
    stage; merged into ``FailedFiles.txt`` by ``write_ecg``.

Filename conventions
--------------------

Writers own their filenames through three pieces of shared machinery
on :class:`~ecgprocess.writer.BaseWriter`:

* ``FILE_EXT`` — a class attribute holding the on-disk extension,
  including the leading dot (e.g. ``'.json'``). Writers that name
  their own files keep the empty default.
* ``file_ext()`` — returns ``FILE_EXT`` by default; override it when
  the extension depends on an option (e.g. a compression suffix).
* ``file_names(chunk_num=None)`` — returns the five standard
  filenames (metadata, waveforms, medianbeats, ecg_data, figures)
  with the chunk suffix and extension applied. Use the slots relevant
  to your format and ignore the rest.

A writer that names its own files (such as the per-record image
writer) may bypass ``file_names`` entirely — but must leave the
inherited method intact: returning the five standard names is part of
the writer contract, and :func:`~ecgprocess.writer.validate_writer`
checks it.

Failure policy
--------------

Errors caused by a malformed configuration should be raised
immediately. For per-record data failures, honour ``ctx.skip_data``:
when it is set, append ``(identifier, cause)`` to
``ctx.failed_records`` and continue with the remaining records —
``write_ecg`` merges the pairs into ``FailedFiles.txt``; when it is
not set, raise an :class:`~ecgprocess.errors.InputValidationError`
naming the record.

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
        def write(self, meta_list, wave_list, median_list, ctx):
            # the fourth standard name is the bundled-output slot
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
        @staticmethod
        def _signals(signal_list):
            """Map numpy arrays to lists, dropping absent leads."""
            return [
                {lead: signal.tolist()
                 for lead, signal in signals.items()
                 if signal is not None}
                for signals in signal_list
            ]

Every piece of the contract appears once: the export flags gate each
source, ``file_names`` supplies the chunk-aware filename, and all
output lands in ``ctx.target``.

Validating your writer
----------------------

:func:`~ecgprocess.writer.validate_writer` checks a writer class or
instance against the contract before a batch run — a light-touch,
data-free pre-flight that never writes files:

.. code-block:: python

    from ecgprocess.writer import validate_writer

    validate_writer(JsonWriter)   # passes silently

All detected violations are collected and raised together as a single
:class:`~ecgprocess.errors.InputValidationError`, so one run reports
everything to fix:

.. code-block:: text

    the supplied writer failed validation with 2 violation(s):
    - a non-empty `FILE_EXT` must start with a dot; got `json`.
    - `file_names()` must return 5 filenames, got 3.

The checks cover: the subclass/instance requirement, unimplemented
abstract methods, the four-argument ``write`` signature (variadic and
extra defaulted parameters are accepted), bare instantiation for class
input, and the filename machinery (``FILE_EXT`` type and dot prefix,
plus the ``file_ext()``/``file_names()`` return types).

Notes
-----

* ``dataclass``-based writers must give every field a default to be
  usable via ``writer=MyWriter``; otherwise pass a configured
  instance.
* Writers defining ``__slots__`` should override ``__repr__``: the
  inherited representation reads ``vars(self)``, which slotted classes
  do not provide.
