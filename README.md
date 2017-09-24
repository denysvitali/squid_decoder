# Squid Decoder

**REQUIRES PYTHON 2**
*cairoffi doesn't seem to work with python3*

[Haxelion](https://github.com/haxelion/) reversed engineered part of [Squid (ex Papyrus) application](http://squidnotes.com/) page storage
format which is based on [Google Protocol Buffers](https://developers.google.com/protocol-buffers/).
He rewrote part of the format `.proto` file and wrote a demonstration script which uses protobuf and
cairo to convert Squid page file into SVG.

[I](https://github.com/denysvitali/) have extended his work adding more features
like Ellipses and Text support

## Background

You can obtain those pages by making a local or cloud backup. This creates a file called
`papyrus.bak` which is in fact a zip file. In the zip you'll find an `info.json` file, a
`papyrus.db` database file and a `data` directory. The pages are located in `data/pages`.

Page names correspond to UUIDs. The database (which is a SQLite3 database) links those UUID with
notes and notebooks.

From a limited reverse engineering of the application you can discover it uses the
[Wire Protocol Buffer](https://github.com/square/wire) to generate java files from Google Protocol
Buffers definition of the Squid Page format. I thus simply reconstructed the `.proto` file from
those reversed java files.

## Limitations

Only the stroke part of the format (which is also used by the rectangle and line tools) is fully
reversed because so far that's the only part I care about. The following features are not reversed
engineered:

* Paper background
* PDF background
* ~~Ellipse tool~~
* ~~Text tool~~
* Image tool

Feel free to open an issue if you need it and encourage me to reverse engineer it. Or send a pull request if you've implemented it.

## Usage

The `page2svg.py` tool can be simply used with the following command:

```
python2 page2svg.py <Input Squid page file> <Output SVG>
```

`page2svg.py` is supposed to demonstrate how you can interpret the Squid Page format.

## Disclaimer

I made this work under the fair assumption it is covered by the exceptions of the section 1201 of
the Digital Millennium Copyright Act: https://www.eff.org/fr/issues/coders/reverse-engineering-faq#faq9
