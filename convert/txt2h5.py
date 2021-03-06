#!/usr/bin/env python
"""Convert ASCII (column) data files to HDF5, and vice-versa.

The program recognizes the type of input file (ASCII or HDF5) 
and performs the conversion accordingly. If the name of the `fields` 
are passed, the columns in the ASCII file will be converted to 1D
arrays in a `Table` given the respective names. Otherwise a 2D array 
named `data` (mirroring the ASCII file) is created.

For the reverse operation (HDF5 to ASCII) specific `fields` can be 
selected for conversion, otherwise all `fields` are converted.

Examples
--------
To see the available options::

  $ python txt2h5.py -h

To convert 3 `cols` of several ASCII files given the name of each 
`field` (column) and specifying a compression lib::

  $ python txt2h5.py -c 1,2,3 -f lon,lat,elev -l zlib /path/to/files/*.txt

To convert some `fields` of an HDF5 `Table` file to ASCII::

  $ python txt2h5.py -f time,lon,lat,temp /path/to/files/*.h5

"""
# Fernando Paolo <fpaolo@ucsd.edu>
# January 1, 2010

import os
import sys
import mimetypes as mt
import argparse as ap
import numpy as np
import tables as tb 

# parse command line arguments
parser = ap.ArgumentParser()
parser.add_argument('files', nargs='+',
    help='file[s] to convert [ex: /path/to/files/*.ext]')
parser.add_argument('-v', dest='verbose', default=False, 
    action='store_const', const=True, 
    help='for verbose [default: run silent]')
parser.add_argument('-arr', dest='array', default=False, 
    action='store_const', const=True, 
    help='creates an HDF5 Array [default: Table]')
parser.add_argument('-carr', dest='carray', default=False, 
    action='store_const', const=True, 
    help='creates an HDF5 CArray w/compression [default: Table]')
parser.add_argument('-f', dest='fields', default=[],
    help='names to be used for the `fields` (columns), ex: -f x,y,z '
    '[default: no columns]')
parser.add_argument('-d', dest='formats', default=[],
    help='data format of the resulting array, ex: -d i4,f8,f4 '
    '[default: f8]')
parser.add_argument('-c', dest='usecols', default=(),
    help='ASCII columns to convert, ex: -c 3,0,1 '
    '[default: all cols]')
parser.add_argument('-l', dest='complib', default='zlib',
    help='compression library to be used: zlib, lzo, bzip2, blosc ' 
    '[default: zlib]')

args = parser.parse_args()
files = args.files
verbose = args.verbose
array = args.array
carray = args.carray
fields = args.fields
formats = args.formats
usecols = args.usecols
complib = args.complib

if fields:
    fields = fields.split(',')
if formats:
    formats = formats.split(',')
else:
    formats = ['f8' for i in range(len(fields))]
if usecols:
    usecols = eval(usecols)

dtype = {'names': fields, 'formats': formats}


def txt_to_h5_tab(fname, dtype={}, usecols=(), complib='zlib'):
    """Converts ASCII column data file to HDF5 Table.

    It uses `dtype`, a dictionary defining the `names` and `formats`
    of the ASCII columns, to create a `Table` with the data in it.
    """
    if os.path.getsize(fname) == 0:
        print 'file is empty!'
        return
    if not dtype['formats']:
        raise IOError, 'must specify `fields`'
    data = np.loadtxt(fname, usecols=usecols)  # data in-memory
    h5f = tb.openFile(os.path.splitext(fname)[0] + '.h5', 'w')
    print 'Table (%d, %d)' % data.shape
    print 'fields:', dtype['names'], dtype['formats']
    print 'compression lib:', complib
    data = np.rec.fromrecords(data, dtype=dtype)  # arr to rec
    filters = tb.Filters(complib=complib, complevel=9)
    outdata = h5f.createTable(h5f.root, 'data', data, filters=filters)
    h5f.close()


def h5_tab_to_txt(fname, fields=[]):
    """Converts HDF5 Table to ASCII file.
    
    If `fields` are passed, only those columns are converted, 
    otherwise convert them all.
    """
    if os.path.getsize(fname) == 0:
        print 'file is empty!'
        return
    h5f = tb.openFile(fname)
    for leaf in h5f.walkNodes('/', classname='Leaf'):
        if not isinstance(leaf, tb.Table):
            raise TypeError, 'object is not a Table!'
        if not fields:
            fields = leaf.colnames
        print 'Table (%d, %d)' % (leaf.nrows, len(fields))
        print 'fields:', fields
        data = np.array([leaf.col(col) for col in fields])
        data = data.T
    np.savetxt(os.path.splitext(fname)[0] + '.txt', data, fmt='%.6f')
    h5f.close()


def txt_to_h5_arr(fname, dtype={}, usecols=()):
    """Converts ASCII column data file to HDF5 Array.

    If `dtype` (a dictionary) with `fields` is passed the ASCII data 
    columns are converted to 1D `Arrays`, otherwise they are converted 
    to a 2D `Array` mirroring the ASCII file.
    """
    if os.path.getsize(fname) == 0:
        print 'file is empty!'
        return
    data = np.loadtxt(fname, usecols=usecols)    # data in-memory
    h5f = tb.openFile(os.path.splitext(fname)[0] + '.h5', 'w')
    if not dtype['names']:
        print '2D Array (%d, %d)' % data.shape
        outdata = h5f.createArray('/', 'data', data)
    else:
        print '1D Arrays (%d x %d)' % data.shape
        print 'fields:', dtype['names'], dtype['formats']
        group = h5f.createGroup('/', 'data')
        for col, field in enumerate(dtype['names']):
            outdata = h5f.createArray(group, field, data[:,col])
    h5f.close()


def txt_to_h5_carr(fname, dtype={}, usecols=(), complib='zlib'):
    """Converts ASCII column data file to HDF5 CArray w/compression.

    If `dtype` (a dictionary) with `fields` is passed the ASCII data 
    columns are converted to 1D `Arrays`, otherwise they are converted 
    to a 2D `Array` mirroring the ASCII file.
    """
    if os.path.getsize(fname) == 0:
        print 'file is empty!'
        return
    data = np.loadtxt(fname, usecols=usecols)    # data in-memory
    h5f = tb.openFile(os.path.splitext(fname)[0] + '.h5', 'w')
    atom = tb.Float64Atom()
    filters = tb.Filters(complib=complib, complevel=9)
    if not dtype['names']:
        print '2D CArray (%d, %d)' % data.shape
        print 'compression lib:', complib
        shape = data.shape
        dataout = h5f.createCArray('/','data', atom=atom, shape=shape,
                                   filters=filters)
        dataout[:] = data
    else:
        print '1D CArrays (%d x %d)' % data.shape
        print 'fields:', dtype['names'], dtype['formats']
        print 'compression lib:', complib
        group = h5f.createGroup('/', 'data')
        for col, field in enumerate(dtype['names']):
            shape = data[:,col].shape
            dataout = h5f.createCArray(group, field, atom=atom, shape=shape,
                                       filters=filters)
            dataout[:] = data[:,col]
    h5f.close()


### TODO
def h5_arr_to_txt(fname, fields=[]):
    """Converts HDF5 Array to ASCII file.
    
    If `fields` are passed, only those columns are converted, 
    otherwise convert them all.
    """
    pass
    '''
    if os.path.getsize(fname) == 0:
        print 'file is empty!'
        return
    h5f = tb.openFile(fname)
    data = [leaf.read() for leaf in h5f.walkNodes('/') \
            if isinstance(leaf, tb.Array)]
    #print 'Table (%d, %d)' % (leaf.nrows, len(fields))
    #print 'fields:', fields
    np.savetxt(os.path.splitext(fname)[0] + '.txt', data, fmt='%.6f')
    h5f.close()
    '''


def main():
    print 'files to convert: %d ' % len(files)
    mime, _ = mt.guess_type(files[0])
    for f in files:
        if verbose: 
            print 'file:', f
        if mime == 'text/plain':
            print 'ASCII -> HDF5 ...'
            if array:
                txt_to_h5_arr(f, dtype, usecols)
            elif carray:
                txt_to_h5_carr(f, dtype, usecols, complib)
            else:
                txt_to_h5_tab(f, dtype, usecols, complib)
        else:
            print 'HDF5 -> ASCII ...'
            if array:
                h5_arr_to_txt(f, dtype['names'])
            else:
                h5_tab_to_txt(f, dtype['names'])
    print 'done.'

if __name__ == '__main__':
    main()
