import os

from Core.Data.MCsquare.mcsquareConfig import MCsquareConfig


class MCsquareFlashConfig(MCsquareConfig):
  def __init__(self):
    super().__init__()

    self.config["NoSpotSize"] = False

  def __getitem__(self, key):
    return self.config[key]

  def __setitem__(self, key, value):
    self.config[key] = value

  def __str__(self):
    return str(self.config)

  def mcsquareFormatted(self) -> str:
    Module_folder = os.path.dirname(os.path.realpath(__file__))
    fid = open(os.path.join(Module_folder, "ConfigTemplate.txt"), 'r')
    Template = fid.read()
    fid.close()

    for key in self.config:
      if type(self.config[key]) == list:
        Template = Template.replace('{' + key.upper() + '}',
                                    str(self.config[key][0]) + " " + str(self.config[key][1]) + " " + str(self.config[key][2]))
      else:
        Template = Template.replace('{' + key.upper() + '}', str(self.config[key]))

    return Template
