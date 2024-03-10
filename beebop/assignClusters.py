from PopPUNK.web import summarise_clusters, sketch_to_hdf5
from PopPUNK.utils import setupDBFuncs
from beebop.utils import get_external_clusters_from_file
import re
import os
import pickle
import csv
import sys

from beebop.poppunkWrapper import PoppunkWrapper
from beebop.filestore import PoppunkFileStore, DatabaseFileStore


def hex_to_decimal(sketches_dict) -> None:
    """
    [Converts all hexadecimal numbers in the sketches into decimal numbers.
    These have been stored in hexadecimal format to not loose precision when
    sending the sketches from the backend to the frontend]

    :param sketches_dict: [dictionary holding all sketches]
    """
    for sample in list(sketches_dict.values()):
        if isinstance(sample['14'][0], str) and \
                re.match('0x.*', sample['14'][0]):
            for x in range(14, 30, 3):
                sample[str(x)] = list(map(lambda x: int(x, 16),
                                          sample[str(x)]))


def get_clusters(hashes_list: list,
                 p_hash: str,
                 fs: PoppunkFileStore,
                 db_paths: DatabaseFileStore,
                 args: dict) -> dict:
    """
    Assign cluster numbers to samples using PopPUNK.

    :param hashes_list: [list of file hashes from all query samples]
    :param p_hash: [project_hash]
    :param fs: [PoppunkFileStore with paths to input files]
    :param db_paths: [DatabaseFileStore which provides paths
        to database files]
    :param args: [arguments for Poppunk's assign function, stored in
        resources/args.json]
    :return dict: [dict with filehash (key) and cluster number (value)]
    """
    # set output directory
    outdir = fs.output(p_hash)
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    # create qc_dict
    qc_dict = {'run_qc': False}

    # create dbFuncs
    dbFuncs = setupDBFuncs(args=args.assign)

    # transform json to dict
    sketches_dict = {}
    for hash in hashes_list:
        sketches_dict[hash] = fs.input.get(hash)

    # convert hex to decimal
    hex_to_decimal(sketches_dict)

    # create hdf5 db
    qNames = sketch_to_hdf5(sketches_dict, outdir)

    # run query assignment
    wrapper = PoppunkWrapper(fs, db_paths, args, p_hash)
    wrapper.assign_clusters(dbFuncs, qc_dict, qNames)

    queries_names, queries_clusters, _, _, _, _, _ = \
        summarise_clusters(outdir, args.assign.species, db_paths.db, qNames)

    #result = {}
    #for i, (name, cluster) in enumerate(zip(queries_names, queries_clusters)):
    #    result[i] = {
    #        "hash": name,
    #        "cluster": cluster
    #    }

    external_clusters_file = fs.previous_query_external_clustering(p_hash)
    print("Previous clusters files is " + external_clusters_file)

    #with open(external_clusters_csv_name) as f:
    #    reader = csv.reader(f, delimiter=',')
    #    for row in reader:
    #        if row[0] == hashes_list[0]:
    #            print("Found hash: " + hashes_list[0])
    #            print(', '.join(row))
    #print("searched all rows")

    external_clusters = get_external_clusters_from_file(external_clusters_file, hashes_list)
    print("External clusters: " + str(external_clusters))
    result = {}
    for i, (name, cluster) in enumerate(external_clusters.items()):
        result[i] = {
            "hash": name,
            "cluster": cluster
        }

    # save a mapping of PopPUNK clusters to external clusters which we'll use to return
    # visualisations
    external_to_poppunk_clusters = {}
    for i, name in enumerate(queries_names):
        external_to_poppunk_clusters[str(external_clusters[name])] = str(queries_clusters[i])
    sys.stderr.write("external to pp clusters mapping:\n")
    sys.stderr.write(str(external_to_poppunk_clusters) + "\n")
    with open(fs.external_to_poppunk_clusters(p_hash), 'wb') as f:
            pickle.dump(external_to_poppunk_clusters, f)

    # save result to retrieve when reloading project results - this
    # overwrites the initial output file written before the assign
    # job ran
    with open(fs.output_cluster(p_hash), 'wb') as f:
        pickle.dump(result, f)

    return result
