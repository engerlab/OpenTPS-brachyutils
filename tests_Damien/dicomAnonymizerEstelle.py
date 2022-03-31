# This code was taken and adapted from https://github.com/KitwareMedical/dicom-anonymizer

import argparse
import ast
import json
import os
import sys
import tqdm

from simple_dicomanonymizer import *

def anonymize(input_path: str, output_path: str,  lookup_path: str, anonymization_actions: dict,
                deletePrivateTags: bool, rename_files: bool) -> None:
    """
    Read data from input path (folder or file) and launch the anonymization.

    :param input_path: Path to a folder or to a file. If set to a folder,
    then cross all over subfiles and apply anonymization.
    :param output_path: Path to a folder or to a file.
    :param csv_path: Path to lookup table csv path.
    :param anonymization_actions: List of actions that will be applied on tags.
    :param deletePrivateTags: Whether to delete private tags.
    :param renameFiles: Whether to remane output files with pseudo.
    """
    # Get input arguments
    input_folder = ''
    output_folder = ''

    if os.path.isdir(input_path):
        input_folder = input_path

    if os.path.isdir(output_path):
        output_folder = output_path
        if input_folder == '':
            output_path = output_folder + os.path.basename(input_path)

    if input_folder != '' and output_folder == '':
        print('Error, please set a correct output folder path')
        sys.exit()

    # Generate list of input file if a folder has been set
    input_files_list = []
    output_files_list = []
    if input_folder == '':
        input_files_list.append(input_path)
        output_files_list.append(output_path)
    else:
        files = os.listdir(input_folder)
        for fileName in files:
            input_files_list.append(input_folder + '/' + fileName)
            output_files_list.append(output_folder + '/' + fileName)

    progress_bar = tqdm.tqdm(total=len(input_files_list))
    for cpt in range(len(input_files_list)):
        anonymize_dicom_file(input_files_list[cpt], output_files_list[cpt], lookup_path, anonymization_actions, deletePrivateTags, rename_files)
        progress_bar.update(1)

    progress_bar.close()


def generate_actions_dictionary(map_action_tag, defined_action_map = {}) -> dict:
    """
    Generate a new dictionary which maps actions function to tags

    :param map_action_tag: link actions to tags
    :param defined_action_map: link action name to action function
    """
    generated_map = {}
    cpt = 0
    for tag in map_action_tag:
        test = [tag]
        action = map_action_tag[tag]

        # Define the associated function to the tag
        if callable(action):
            action_function = action
        else:
            action_function = defined_action_map[action] if action in defined_action_map else eval(action)

        # Generate the map
        if cpt == 0:
            generated_map = generate_actions(test, action_function)
        else:
            generated_map.update(generate_actions(test, action_function))
        cpt += 1

    return generated_map


def main(defined_action_map = {}):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('input', help='Path to the input dicom file or input directory which contains dicom files')
    parser.add_argument('output', help='Path to the output dicom file or output directory which will contains dicom files')
    parser.add_argument('-t', action='append', nargs='*', help='tags action : Defines a new action to apply on the tag.'\
    '\'regexp\' action takes two arguments: '\
        '1. regexp to find substring '\
        '2. the string that will replace the previous found string')
    parser.add_argument('--lookup', action='store', help='Path to the lookup table to be written after pseudonymization')
    parser.add_argument('--dictionary', action='store', help='File which contains a dictionary that can be added to the original one')
    parser.add_argument('--keepPrivateTags', action='store_true', dest='keepPrivateTags', help='If used, then private tags won\'t be deleted')
    parser.set_defaults(keepPrivateTags=False)
    parser.add_argument('--renameFiles', action='store_true', dest='renameFiles', help="If used, rename output files using PaitentID + AccessionNumber")
    parser.set_defaults(renameFiles=False)
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output

    # Create a new actions' dictionary from parameters
    new_anonymization_actions = {}
    cpt = 0
    if args.t:
        number_of_new_tags_actions = len(args.t)
        if number_of_new_tags_actions > 0:
            for i in range(number_of_new_tags_actions):
                current_tag_parameters = args.t[i]

                nb_parameters = len(current_tag_parameters)
                if nb_parameters == 0:
                    continue

                options = None
                action_name = current_tag_parameters[1]

                # Means that we are in regexp mode
                if nb_parameters == 4:
                    options = {
                        "find": current_tag_parameters[2],
                        "replace": current_tag_parameters[3]
                    }

                tags_list = [ast.literal_eval(current_tag_parameters[0])]

                action = eval(action_name)
                # When generate_actions is called and we have options, we don't want use regexp
                # as an action but we want to call it to generate a new method
                if options is not None:
                    action = action_name

                if cpt == 0:
                    new_anonymization_actions = generate_actions(tags_list, action, options)
                else:
                    new_anonymization_actions.update(generate_actions(tags_list, action, options))
                cpt += 1

    # Read an existing dictionary
    if args.dictionary:
        with open(args.dictionary) as json_file:
            data = json.load(json_file)
            for key, value in data.items():
                action_name = value
                options = None
                if type(value) is dict:
                    action_name = value['action']
                    options = {
                        "find": value['find'],
                        "replace" : value['replace']
                    }

                l = [ast.literal_eval(key)]
                action = defined_action_map[action_name] if action_name in defined_action_map else eval(action_name)
                if cpt == 0:
                    new_anonymization_actions = generate_actions(l, action, options)
                else:
                    new_anonymization_actions.update(generate_actions(l, action, options))
                cpt += 1

    # Launch the anonymization
    anonymize(input_path, output_path, args.lookup, new_anonymization_actions, not args.keepPrivateTags, args.renameFiles)

if __name__ == "__main__":
    main()

## ---------------------------------------------------------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------
# This code was taken and adapted from https://github.com/KitwareMedical/dicom-anonymizer

import os
import re
from typing import List, NewType

import pydicom
from random import randint

#from dicom_fields import *
#from format_tag import tag_to_hex_strings

import hashlib
import csv
import numpy as np

dictionary = {}
lookup_path = None


# Regexp function

def regexp(options: dict):
    """
    Apply a regexp method to the dataset

    :param options: contains two values:
        - find: which string should be find
        - replace: string that will replace the find string
    """

    def apply_regexp(dataset, tag):
        """
        Apply a regexp to the dataset
        """
        element = dataset.get(tag)
        if element is not None:
            element.value = re.sub(options['find'], options['replace'], str(element.value))

    return apply_regexp


# Default anonymization functions

def replace_element_UID(element):
    """
    Keep char value but replace char number with random number
    The replaced value is kept in a dictionary link to the initial element.value in order to automatically
    apply the same replaced value if we have an other UID with the same value
    """
    if element.value not in dictionary:
        new_chars = [str(randint(0, 9)) if char.isalnum() else char for char in element.value]
        dictionary[element.value] = ''.join(new_chars)
    element.value = dictionary.get(element.value)


def replace_element_date(element):
    """
    Replace date element's value with '00010101'
    """
    element.value = '00010101'


def replace_element_date_time(element):
    """
    Replace date time element's value with '00010101010101.000000+0000'
    """
    element.value = '00010101010101.000000+0000'


def replace_element(element):
    """
    Replace element's value according to it's VR:
    - DA: cf replace_element_date
    - TM: replace with '000000.00'
    - LO, SH, PN, CS: replace with 'Anonymized'
    - UI: cf replace_element_UID
    - IS: replace with '0'
    - FD, FL, SS, US: replace with 0
    - ST: replace with ''
    - SQ: call replace_element for all sub elements
    - DT: cf replace_element_date_time
    """
    if element.VR == 'DA':
        replace_element_date(element)
    elif element.VR == 'TM':
        element.value = '000000.00'
    elif element.VR in ('LO', 'SH', 'PN', 'CS'):
        element.value = 'Anonymized'
    elif element.VR == 'UI':
        replace_element_UID(element)
    elif element.VR == 'UL':
        pass
    elif element.VR == 'IS':
        element.value = '0'
    elif element.VR in ('FD', 'FL', 'SS', 'US'):
        element.value = 0
    elif element.VR == 'ST':
        element.value = ''
    elif element.VR == 'SQ':
        for sub_dataset in element.value:
            for sub_element in sub_dataset.elements():
                replace_element(sub_element)
    elif element.VR == 'DT':
        replace_element_date_time(element)
    else:
        raise NotImplementedError('Not anonymized. VR {} not yet implemented.'.format(element.VR))


def replace(dataset, tag):
    """
    D - replace with a non-zero length value that may be a dummy value and consistent with the
    VR
    """
    element = dataset.get(tag)
    if element is not None:
        replace_element(element)


def empty_element(element):
    """
    Clean element according to the element's VR:
    - SH, PN, UI, LO, CS: value will be set to ''
    - DA: value will be replaced by '00010101'
    - TM: value will be replaced by '000000.00'
    - UL: value will be replaced by 0
    - SQ: all subelement will be called with "empty_element"
    """
    if (element.VR in ('SH', 'PN', 'UI', 'LO', 'CS')):
        element.value = ''
    elif element.VR == 'DA':
        replace_element_date(element)
    elif element.VR == 'TM':
        element.value = '000000.00'
    elif element.VR == 'UL':
        element.value = 0
    elif element.VR == 'SQ':
        for sub_dataset in element.value:
            for sub_element in sub_dataset.elements():
                empty_element(sub_element)
    else:
        raise NotImplementedError('Not anonymized. VR {} not yet implemented.'.format(element.VR))


def empty(dataset, tag):
    """
    Z - replace with a zero length value, or a non-zero length value that may be a dummy value and
    consistent with the VR
    """
    element = dataset.get(tag)
    if element is not None:
        empty_element(element)


def delete_element(dataset, element):
    """
    Delete the element from the dataset.
    If VR's element is a date, then it will be replaced by 00010101
    """
    if element.VR == 'DA':
        replace_element_date(element)
    elif element.VR == 'SQ' and element.value is type(pydicom.Sequence):
        for sub_dataset in element.value:
            for sub_element in sub_dataset.elements():
                delete_element(sub_dataset, sub_element)
    else:
        del dataset[element.tag]


def delete(dataset, tag):
    """X - remove"""
    element = dataset.get(tag)
    if element is not None:
        delete_element(dataset, element)  # element.tag is not the same type as tag.


def keep(dataset, tag):
    """K - keep (unchanged for non-sequence attributes, cleaned for sequences)"""
    pass


def clean(dataset, tag):
    """
    C - clean, that is replace with values of similar meaning known not to contain identifying
    information and consistent with the VR
    """
    if dataset.get(tag) is not None:
        raise NotImplementedError('Tag not anonymized. Not yet implemented.')


def replace_UID(dataset, tag):
    """
    U - replace with a non-zero length UID that is internally consistent within a set of Instances
    Lazy solution : Replace with empty string
    """
    element = dataset.get(tag)
    if element is not None:
        replace_element_UID(element)


def empty_or_replace(dataset, tag):
    """Z/D - Z unless D is required to maintain IOD conformance (Type 2 versus Type 1)"""
    replace(dataset, tag)


def delete_or_empty(dataset, tag):
    """X/Z - X unless Z is required to maintain IOD conformance (Type 3 versus Type 2)"""
    empty(dataset, tag)


def delete_or_replace(dataset, tag):
    """X/D - X unless D is required to maintain IOD conformance (Type 3 versus Type 1)"""
    replace(dataset, tag)


def delete_or_empty_or_replace(dataset, tag):
    """
    X/Z/D - X unless Z or D is required to maintain IOD conformance (Type 3 versus Type 2 versus
    Type 1)
    """
    replace(dataset, tag)


def delete_or_empty_or_replace_UID(dataset, tag):
    """
    X/Z/U* - X unless Z or replacement of contained instance UIDs (U) is required to maintain IOD
    conformance (Type 3 versus Type 2 versus Type 1 sequences containing UID references)
    """
    element = dataset.get(tag)
    if element is not None:
        if element.VR == 'UI':
            replace_element_UID(element)
        else:
            empty_element(element)


def replace_and_keep_correspondence(dataset, tag):
    if lookup_path is None:
        raise ValueError("Missing path to lookup table to save correspondence")
    if os.path.exists(lookup_path):
        with open(lookup_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            data = np.array(list(reader))
    else:
        data = np.array([['old_patient_id', 'new_patient_id', 'old_accession_number', 'new_accession_number']])

    data_changed = True
    element = dataset.get(tag)
    if element is not None:
        new_value_patient_id = hashlib.sha256((str(dataset.PatientID) + str(os.urandom(32))).encode()).hexdigest()
        new_value_accession_number = hashlib.sha256(
            (str(dataset.AccessionNumber) + str(os.urandom(32))).encode()).hexdigest()
        if element.VR == "LO":  # Patient ID
            if element.value not in data[:, 0]:  # Patient not in csv
                data = np.append(data, [[str(dataset.PatientID), new_value_patient_id, str(dataset.AccessionNumber),
                                         new_value_accession_number]], axis=0)
                dataset.PatientID = new_value_patient_id
                dataset.AccessionNumber = new_value_accession_number
            else:  # Patient in csv
                if dataset.AccessionNumber in data[:, 2]:  # AccessNumber in csv
                    idx = np.argwhere(data[:, 2] == str(dataset.AccessionNumber))[0][0]
                    dataset.AccessionNumber = data[idx, 3]
                    dataset.PatientID = data[idx, 1]
                    data_changed = False
                else:  # AccessNumber not in csv
                    idx = np.argwhere(data[:, 0] == str(dataset.PatientID))[0][0]
                    data = np.append(data, [
                        [data[idx, 0], data[idx, 1], str(dataset.AccessionNumber), new_value_accession_number]], axis=0)
                    dataset.PatientID = data[idx, 1]
                    dataset.AccessionNumber = new_value_accession_number

    if data_changed:
        np.savetxt(lookup_path, data, delimiter=',', fmt="%s")


# Generation functions

actions_map_name_functions = {
    "replace": replace,
    "empty": empty,
    "delete": delete,
    "replace_UID": replace_UID,
    "empty_or_replace": empty_or_replace,
    "delete_or_empty": delete_or_empty,
    "delete_or_replace": delete_or_replace,
    "delete_or_empty_or_replace": delete_or_empty_or_replace,
    "delete_or_empty_or_replace_UID": delete_or_empty_or_replace_UID,
    "replace_and_keep_correspondance": replace_and_keep_correspondence,
    "keep": keep,
    "regexp": regexp
}


def generate_actions(tag_list: list, action, options: dict = None) -> dict:
    """
    Generate a dictionary using list values as tag and assign the same value to all

    :param tag_list: list of tags which will have the same associated actions
    :param action: define the action that will be use. It can be a callable custom function or a name of a pre-defined
    action from simpledicomanonymizer.
    :param options: Define options tht will be affected to the action (like regexp)
    """
    final_action = action
    if not callable(action):
        final_action = actions_map_name_functions[action] if action in actions_map_name_functions else keep
    if options is not None:
        final_action = final_action(options)
    return {tag: final_action for tag in tag_list}


def initialize_actions() -> dict:
    """
    Initialize anonymization actions with DICOM standard values

    :return Dict object which map actions to tags
    """
    anonymization_actions = generate_actions(D_TAGS, replace)
    anonymization_actions.update(generate_actions(Z_TAGS, empty))
    anonymization_actions.update(generate_actions(X_TAGS, delete))
    anonymization_actions.update(generate_actions(U_TAGS, replace_UID))
    anonymization_actions.update(generate_actions(Z_D_TAGS, empty_or_replace))
    anonymization_actions.update(generate_actions(X_Z_TAGS, delete_or_empty))
    anonymization_actions.update(generate_actions(X_D_TAGS, delete_or_replace))
    anonymization_actions.update(generate_actions(X_Z_D_TAGS, delete_or_empty_or_replace))
    anonymization_actions.update(generate_actions(X_Z_U_STAR_TAGS, delete_or_empty_or_replace_UID))
    anonymization_actions.update(generate_actions(P_TAGS, replace_and_keep_correspondence))
    return anonymization_actions


def anonymize_dicom_file(in_file: str, out_file: str, lookup_file: str = None, extra_anonymization_rules: dict = None,
                         delete_private_tags: bool = True, rename_files: bool = False) -> None:
    """
    Anonymize a DICOM file by modifying personal tags

    Conforms to DICOM standard except for customer specificities.

    :param in_file: File path or file-like object to read from
    :param out_file: File path or file-like object to write to
    :param lookup_file: File path to the lookup table.
    :param extra_anonymization_rules: add more tag's actions
    :param delete_private_tags: Define if private tags should be delete or not
    """
    if (os.path.isfile(in_file)):
        dataset = pydicom.dcmread(in_file, force=True)

        global lookup_path
        lookup_path = lookup_file

        anonymize_dataset(dataset, extra_anonymization_rules, delete_private_tags)

        # Store modified image
        if rename_files:
            start_file_name = out_file.rfind('/')
            pseudo = str(dataset.PatientID) + '-' + str(dataset.AccessionNumber)
            num_file = str(len(os.listdir(out_file[:start_file_name])))
            full_out_path = out_file[:start_file_name] + num_file + '_' + pseudo
            dataset.save_as(full_out_path)
        else:
            dataset.save_as(out_file)


def get_private_tag(dataset, tag):
    """
    Get the creator and element from tag

    :param dataset: Dicom dataset
    :param tag: Tag from which we want to extract private information
    :return dictionary with creator of the tag and tag element (which contains element + offset)
    """
    element = dataset.get(tag)

    element_value = element.value
    tag_group = element.tag.group
    # The element is a private creator
    if element_value in dataset.private_creators(tag_group):
        creator = {
            "tagGroup": tag_group,
            "creatorName": element.value
        }
        private_element = None
    # The element is a private element with an associated private creator
    else:
        # Shift the element tag in order to get the create_tag
        # 0x1009 >> 8 will give 0x0010
        create_tag_element = element.tag.element >> 8
        create_tag = pydicom.tag.Tag(tag_group, create_tag_element)
        create_dataset = dataset.get(create_tag)
        creator = {
            "tagGroup": tag_group,
            "creatorName": create_dataset.value
        }
        # Define which offset should be applied to the creator to find
        # this element
        # 0x0010 << 8 will give 0x1000
        offset_from_creator = element.tag.element - (create_tag_element << 8)
        private_element = {
            "element": element,
            "offset": offset_from_creator
        }

    return {
        "creator": creator,
        "element": private_element
    }


def get_private_tags(anonymization_actions: dict, dataset: pydicom.Dataset) -> List[dict]:
    """
    Extract private tag as a list of object with creator and element

    :param anonymization_actions: list of tags associated to an action
    :param dataset: Dicom dataset which will be anonymize and contains all private tags
    :return Array of object
    """
    private_tags = []
    for tag, action in anonymization_actions.items():
        try:
            element = dataset.get(tag)
        except:
            print("Cannot get element from tag: ", tag_to_hex_strings(tag))

        if element and element.tag.is_private:
            private_tags.append(get_private_tag(dataset, tag))

    return private_tags


def anonymize_dataset(dataset: pydicom.Dataset, extra_anonymization_rules: dict = None,
                      delete_private_tags: bool = True) -> None:
    """
    Anonymize a pydicom Dataset by using anonymization rules which links an action to a tag

    :param dataset: Dataset to be anonymize
    :param extra_anonymization_rules: Rules to be applied on the dataset
    :param delete_private_tags: Define if private tags should be delete or not
    """
    current_anonymization_actions = initialize_actions()

    if extra_anonymization_rules is not None:
        current_anonymization_actions.update(extra_anonymization_rules)

    private_tags = []

    for tag, action in current_anonymization_actions.items():

        def range_callback(dataset, data_element):
            if data_element.tag.group & tag[2] == tag[0] and data_element.tag.element & tag[3] == tag[1]:
                action(dataset, tag)

        element = None

        # We are in a repeating group
        if len(tag) > 2:
            dataset.walk(range_callback)
        # Individual Tags
        else:
            action(dataset, tag)
            try:
                element = dataset.get(tag)
            except:
                print("Cannot get element from tag: ", tag_to_hex_strings(tag))

            # Get private tag to restore it later
            if element and element.tag.is_private:
                private_tags.append(get_private_tag(dataset, tag))

    # X - Private tags = (0xgggg, 0xeeee) where 0xgggg is odd
    if delete_private_tags:
        dataset.remove_private_tags()

        # Adding back private tags if specified in dictionary
        for privateTag in private_tags:
            creator = privateTag["creator"]
            element = privateTag["element"]
            block = dataset.private_block(creator["tagGroup"], creator["creatorName"], create=True)
            if element is not None:
                block.add_new(element["offset"], element["element"].VR, element["element"].value)


## ---------------------------------------------------------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------
# This code was taken and adapted from https://github.com/KitwareMedical/dicom-anonymizer

"""
Utility for printing the tags in the original hex format.
"""

def hex_to_string(x):
    """
    Convert a tag number to it's original hex string.

    E.g. if a tag has the hex number 0x0008, it becomes 8,
    and we then convert it back to 0x0008 (as a string).
    """
    x = str(hex(x))
    left = x[:2]
    right = x[2:]
    num_zeroes = 4 - len(right)
    return left + ('0'*num_zeroes) + right

def tag_to_hex_strings(tag):
    """
    Convert a tag tuple to a tuple of full hex number strings.

    E.g. (0x0008, 0x0010) is evaluated as (8, 16) by python. So
    we convert it back to a string '(0x0008, 0x0010)' for pretty printing.
    """
    return tuple([hex_to_string(tag_element) for tag_element in tag])