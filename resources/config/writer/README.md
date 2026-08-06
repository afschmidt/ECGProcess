# XMLWriter configuration templates

`XMLWriter` (`writer='xml'`) writes one XML document per ECG UID.
You tell it what the document should look like with a *template*: a
description of the XML written in JSON, with a few of its values
swapped out for references to that record's data.
This page covers how a template turns into XML, the rule that tells a 
literal value apart from a data reference, and (optional) XSD validation.

## How the template maps to XML

The XML template is written in JSON, a plain text format for storing
structured data as named values, widely used for configuration files
and for passing data between programs.
JSON groups values: 1) a dictionary holds named values, each name is
called a key, paired with its value; 2) a list holds an ordered sequence of 
values with no names attached.
A template is one such dictionary (or a path to a JSON file
holding one).
Its shape *is* the XML structure: writing the template
is really just writing XML using this dictionary and list form
instead of angle brackets.

| In the template | Becomes, in the XML |
|---|---|
| The one top-level key | The root element |
| A key starting with `@`, e.g. `"@name"` | An attribute on the enclosing element |
| The key `#text` | The enclosing element's text content |
| A key with a dictionary value | A child element, built from that dictionary the same way |
| A key with a list value | The element repeated once per item in the list |
| A key with a plain string/number value | Shorthand for a child element whose only content is that value |

This mapping is not specific to ECGProcess: it comes directly from
`xmltodict`, a widely used Python library that converts between XML
documents and this same JSON dictionary/list form.
See the example JSON snippet:

```json
{
    "ECGExport": {
        "@id": "MetaData.unique identifier",
        "@schemaVersion": "1.0",
        "SamplingFrequency": "MetaData.sampling frequency (original)",
        "WaveForms": {
            "Lead": [
                {"@name": "I", "#text": "WaveForms.I"}
            ]
        },
        "MedianBeats": {
            "Lead": [
                {"@name": "I", "#text": "MedianBeats.I"}
            ]
        }
    }
}
```

This produces an `<ECGExport>` root element with `id` and
`schemaVersion` attributes, a `<SamplingFrequency>` child, and a
`<WaveForms>` child containing one `<Lead name="I">` element per list
entry (and likewise for `<MedianBeats>`).

## Literals and data references

The one piece that is not plain `xmltodict`: a string value, a piece
of text, can also be a *reference* into the dictionary keys internally
created by `ECGTable`, rather than literal text.
A string is read as a reference only when the text before its first dot 
matches a data source exactly
(`MetaData`, `WaveForms`, or `MedianBeats`), as in
`"MetaData.unique identifier"` above. Every other string is written
out exactly as given, which is how a fixed value like
`"@schemaVersion": "1.0"` stays `"1.0"` for every record. Numbers,
booleans (JSON's true and false values), and `null` (JSON's way of
writing "no value") are always literals; only strings are ever read
as references.

Two things follow from that rule:

* A misspelled source is silently a literal, not an error. For
  example, `"metadata.unique identifier"` does not match any source, so
  it is written out as that literal text.
* A source name matched in every way but case raises
  `InputValidationError` when you set up the writer (when the
  `XMLWriter` is created, before it processes any records).
  For example, `"metadata.unique identifier"` or `"WAVEFORMS.I"` is treated as a
  typo, not a literal.
  So a genuine literal that happens to start with a source name in a different 
  case (a filename like `"metadata.xml"` used as an attribute value) needs
  rewording to avoid the clash.

## XSD validation

You can pass an (optional) XSD file using `xsd_path` to validate every document 
against that schema before it is written.
This ensures the outputted files adhere the XSD structure and allows
for direct quality control of XML before written to disk. 
The schema is parsed once per writer instance and reused for every
record.


### Writing your own XSD

An XSD is a set of rules for what your XML is allowed to look like:
which elements can appear, in what order, what attributes they carry,
and what type their content is. If you have not written one before,
read the below alongside the shipped example schema. 

```xml
<xs:element name="ECGExport">
  <xs:complexType>
    <xs:sequence>
      <xs:element name="SamplingFrequency" type="xs:decimal"/>
      <xs:element name="WaveForms" type="LeadGroupType"/>
      <xs:element name="MedianBeats" type="LeadGroupType"/>
    </xs:sequence>
    <xs:attribute name="id" type="xs:string" use="required"/>
    <xs:attribute name="schemaVersion" type="xs:string" use="required"/>
  </xs:complexType>
</xs:element>
```

Reading it piece by piece:

* `<xs:element name="ECGExport">` declares the root element. Its
  `name` must match the JSON template's one top-level key.
* `<xs:sequence>` lists, in order, the child elements `ECGExport`
  must contain: `SamplingFrequency`, then `WaveForms`, then
  `MedianBeats`. This order is not just documentation: validation
  fails if the elements come out in a different order, and since
  `xmltodict` writes each dict out in the order you wrote its keys,
  that means your template's key order has to match the schema.
* `<xs:attribute name="id" .../>` and `.../"schemaVersion"` sit next
  to `xs:sequence`, not inside it, which is what makes them attributes
  on `ECGExport` (matching the JSON template's `@id`/`@schemaVersion`)
  rather than child elements. `use="required"` fails validation if
  the attribute is missing.
* `type="xs:decimal"` / `type="xs:string"` say what kind of value is
  allowed. `xs:string`, `xs:decimal`, and `xs:boolean` cover most ECG
  fields.

One shape looks different: an element that carries both an attribute
*and* text, with no child elements of its own. In the example that is
`Lead` (`<Lead name="I">WaveForms.I</Lead>`):

```xml
<xs:element name="Lead" maxOccurs="unbounded">
  <xs:complexType>
    <xs:simpleContent>
      <xs:extension base="xs:string">
        <xs:attribute name="name" type="xs:string" use="required"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>
</xs:element>
```

`xs:sequence` only describes an element's *child elements*, and
`Lead` has none, just text, so it cannot be written that way.
`xs:simpleContent`/`xs:extension` is the XSD way of saying "this
element's content is a string, plus this attribute." Use this
whenever an element mixes text and an attribute together, and plain
`xs:sequence`/`xs:element` the rest of the time. `maxOccurs="unbounded"`
is what allows any number of `Lead` elements, matching the template's
`Lead` list.

### XML namespace (Optional)

Two XML terms are worth explaining here, since they only matter if
your schema uses them:

* **`xmlns`** is how an XML document says "the elements in here
  belong to this named vocabulary." It is written as an attribute,
  e.g. `xmlns="urn:hl7-org:v3"` on an element, and it applies to that
  element and everything nested inside it. It exists so that two
  unrelated XML formats which both happen to use an element called,
  say, `<id>`, do not get confused with each other if a document ever
  needs to combine both.
* **`targetNamespace`** is the schema-side version of the same idea:
  an attribute on a schema's `<xs:schema>` root saying "every element
  this schema defines belongs to this namespace." If a schema
  declares one, a document being validated against it must carry a
  matching `xmlns`, or the validator will not recognise the root
  element as the one the schema describes.

Neither is required. Most single-purpose schemas, including the
shipped example (`list_xml_writer_paths()['example_1_schema']`), have
no `targetNamespace` and validate plain, unnamespaced XML just fine.
You only need one if you are combining your export with another XML
vocabulary in the same document, or matching an existing external
standard that already specifies a namespace (HL7's aECG format, for
example, uses `urn:hl7-org:v3`).

If your schema *does* declare a `targetNamespace`, remember that
`xmltodict` does not add an `xmlns` attribute on its own. The
template needs that namespace written in as a literal attribute, e.g.
`"@xmlns": "urn:hl7-org:v3"`. Skip it and every document fails
validation with an error like `No matching global declaration
available for the validation root`; that message is the tell that the
root element needs its namespace declared.

### Splitting a schema across files (Optional)

If your schema grows large enough that you want to split its rules
across several XSD files, XSD gives you `xs:include` and `xs:import`
for this: elements placed inside one XSD file that tell the validator
"also read the rules in this other file, and treat them as part of
this schema." Each one names the other file with a `schemaLocation`
attribute, a file path written relative to the XSD file it appears in
(for example, `schemaLocation="leads.xsd"` looks for `leads.xsd` in
the same folder). To use a schema split this way, point `xsd_path` at
the entry file, the one the other files are included into, and keep
the included files next to it. `XMLWriter` parses the schema from its
path, which resolves those relative references against the schema
file's own directory regardless of your current working directory,
so you do not need to preload the included files yourself.

## Failure handling

A missing template, or a template referencing a data source that was
not extracted, raises immediately, before anything is written. A
per-record problem, a missing field or a schema failure, follows the
usual writer failure policy: skip and record it if the caller opted
in, otherwise raise. See {doc}`custom_writers`'s Failure policy
section for the shared mechanics.

## See also

- {doc}`writers`: how `XMLWriter` compares to the other built-in
  writers
- {doc}`custom_writers`: the shared `WriteContext` and failure-policy
  machinery every writer follows
