#!/usr/bin/python
# -*- coding: utf-8 -*-
# Python 3 PyQt5

import sys, os

from PyQt5 import (QtCore, QtGui, QtWidgets)


#############################################################################
class FileDialog(QtWidgets.QFileDialog):

    # ========================================================================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ========================================================================
    def getSaveFileName(self, parent=None,
                        caption="Sélectionnez un fichier",
                        dir=".",
                        filter="All files (*.*)",
                        selectedFilter="",
                        options=None):

        # --------------------------------------------------------------------
        # configuration de la fenêtre de dialogue: à vérifier que c'est complet!
        self.setWindowTitle(caption)
        self.setDirectory(dir)
        self.setNameFilter(filter)
        self.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)  # bouton "Ouvrir"
        if selectedFilter != "":
            self.selectNameFilter(selectedFilter)
        if options != None:
            self.setOptions(options)

        self.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)

        # --------------------------------------------------------------------
        # on ajoute un QCheckBox à la fenêtre de dialogue
        layout = self.layout()
        self.cbox = QtWidgets.QCheckBox("Mon checkbox", self)
        layout.addWidget(self.cbox, 4, 0)
        self.setLayout(layout)

        # on va cocher la case à titre d'exemple
        self.cbox.setCheckState(QtCore.Qt.Checked)

        # --------------------------------------------------------------------
        # interaction avec l'utilisateur et retour du résultat
        if self.exec_():
            return list(self.selectedFiles())[0]
        else:
            return ""


#############################################################################
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    fileDialog = FileDialog()
    fichier = fileDialog.getSaveFileName(None, "titre")
    print(fichier)