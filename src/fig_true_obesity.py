from osgeo import ogr
import matplotlib.path as mpath
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import os, csv
from math import ceil, floor

cities = ['stb', 'memphis', 'san-antonio', 'lacity']
# cities = ['stb']

cmapstring = 'YlGnBu'
out_file_suffix = '_true_obesity'

# cmapstring = 'RdBu_r'
# out_file_suffix = '_true_obesity_poi'

# cmapstring = 'PRGn'
# out_file_suffix = '_true_income'

datadir = '../data'


def readObfile(obfile):

    tractids = []
    obvalues = {}
    skipped = 0
    with open(obfile, 'r') as f:
        obreader = csv.reader(f)
        header = next(obreader)
        for i in range(0, len(header)):
            if header[i] == 'TractFIPS':
                tractind = i
                continue
            if header[i] == 'GeographicLevel':
                levelind = i
                continue
            if header[i] == 'Data_Value':
                dataind = i
                continue
        for row in obreader:
            if row[levelind] != 'Census Tract':
                continue
            if row[dataind] == '':
                #print(row)
                skipped += 1
                continue
            tractids.append(row[tractind])
            obvalues[row[tractind]] = float(row[dataind])
    print('Total number of census tracts considered from datafile: ', len(tractids))
    print('Total number of census tracts ignored from datafile (due to population < 50): ', skipped)
    return tractids, obvalues

for city in cities:
    cols = []

    tractids, obvalues = readObfile(os.path.join(datadir, city, '500_cities_' + city + '_obesity.csv'))
    #print(tractids)
    #plt.hist(list(obvalues.values()), bins = 30)
    #plt.show()

    # Extract first layer of features from shapefile using OGR
    shpfiles = [f for f in os.listdir(os.path.join('../data', city, 'mapping')) if f.endswith('.shp')]
    if len(shpfiles) > 1:
        print('Multiple shape files in directory')
        break
    else:
        shapefile = shpfiles[0]

    ds = ogr.Open(os.path.join('../data', city, 'mapping', shapefile))
    nlay = ds.GetLayerCount()
    lyr = ds.GetLayer(0)

    # Get extent and calculate buffer size
    ext = lyr.GetExtent()
    xoff = (ext[1] - ext[0]) / 50
    yoff = (ext[3] - ext[2]) / 50

    # Prepare figure
    fig = plt.figure(figsize=(5, 5))
    ax = fig.add_subplot(111)
    ax.set_xlim(ext[0] - (0.2 * xoff), ext[1] + (0.2 * xoff))
    ax.set_ylim(ext[2] - (0.4 * yoff), ext[3] + (0.1 * yoff))

    paths = []
    lyr.ResetReading()

    # Read all features in layer and store as paths
    skipped = 0
    tractlist = []
    for feat in lyr:
        geom = feat.geometry()
        # print(feat['tract2010'], geom.GetGeometryCount())
        codes = []
        all_x = []
        all_y = []
        for i in range(geom.GetGeometryCount()):
            # Read ring geometry and create path
            r = geom.GetGeometryRef(i)
            if r.GetGeometryName() == 'POLYGON':
                for n in range(r.GetGeometryCount()):
                    rpoly = r.GetGeometryRef(n)
                    assert rpoly.GetGeometryName() == 'LINEARRING'
                    x = [rpoly.GetX(m) for m in range(rpoly.GetPointCount())]
                    y = [rpoly.GetY(m) for m in range(rpoly.GetPointCount())]
                    codes += [mpath.Path.MOVETO] + (len(x) - 1) * [mpath.Path.LINETO]
                    all_x += x
                    all_y += y
                continue
            elif r.GetGeometryName() == 'LINEARRING':
                # print(i, r.GetGeometryName(), r, r.GetPointCount())
                x = [r.GetX(j) for j in range(r.GetPointCount())]
                y = [r.GetY(j) for j in range(r.GetPointCount())]
                # skip boundary between individual rings
                codes += [mpath.Path.MOVETO] + (len(x) - 1) * [mpath.Path.LINETO]
                all_x += x
                all_y += y
            else:
                print('Unknown geometry: ', r.GetGeometryName())

        if all_x == []:
            print('skipped')
            skipped += 1
            continue
        tractlist.append(feat['tract2010'])
        path = mpath.Path(np.column_stack((all_x, all_y)), codes)
        paths.append(path)
    print('Total number of census tracts considered from shapefile: ', len(tractlist))
    print('Total number of census tracts ignored from shapefile: ', skipped)
    
    blues = plt.get_cmap(cmapstring)
    pccmax = max(obvalues.values())
    pccmin = min(obvalues.values())
    print(pccmin, pccmax)
    counter = 0
    mapped_true = 0
    for path in paths:
        fcol = "0.5"
        try:
            pcc = obvalues[tractlist[counter]]
            pcc_norm = (pcc - pccmin) / (pccmax - pccmin)
            fcol = blues(pcc_norm)
            mapped_true += 1
        except (KeyError, ValueError) as e:
            fcol = "0.5"
        patch = mpatches.PathPatch(path, facecolor=fcol, edgecolor='white', linewidth=0.2)
        ax.add_patch(patch)
        counter += 1
    print('Total number of census tracts mapped to true values: ', mapped_true)

    ticks = list(np.linspace(pccmin, pccmax, 10))
    ticks = [round(num, 1) for num in ticks]
    sm = plt.cm.ScalarMappable(cmap=cmapstring, norm=plt.Normalize(vmin=int(floor(pccmin)), vmax=int(ceil(pccmax))))
    sm._A = []
    cbar = plt.colorbar(sm, orientation='horizontal', fraction=0.040, pad=0.04, ticks = ticks)
    cbar.outline.set_linewidth(0.3)
    print(ticks)
    cbar.ax.set_xticklabels(ticks, fontsize=5, weight='bold') # change fontsize to 25 with 300 dpi

    ax.set_aspect(1.0)
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    # plt.title('True crime rate in Chicago (by census tract)')
    plt.savefig(os.path.join('../out', city, city + out_file_suffix + '.tiff'), bbox_inches='tight', dpi=300)
