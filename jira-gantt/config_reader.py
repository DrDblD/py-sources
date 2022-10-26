import configparser

class Config():
    DEFAULT_KEY = 'DEFAULT'
    def __init__(self, filename=None):
        self.parser = configparser.ConfigParser()
        if filename:
            self.read_parameters(filename)
    
    def read_parameters(self, filename):
        self.parser.read(filename)
    
    def getter(self, parameter, section=DEFAULT_KEY):
        return self.parser.get(section, parameter, fallback='No such {} in {} section'.format(parameter, section))
        # return self.parser.get(section, parameter)
    
    def alt_getter(self, **kwargs):
        if "section" in kwargs and "parameter" in kwargs:
            return self.parser[kwargs.get("section")][kwargs.get("parameter")]
        elif "section" in kwargs and "parameter" not in kwargs:
            return self.parser[kwargs.get("section")]
        elif "parameter" in kwargs and "section" not in kwargs:
            self.parser[self.DEFAULT_KEY][kwargs.get("parameter")]
        else: 
            return self.parser
    
    @property
    def sections(self):
        return self.parser.sections()

if __name__ == "__main__":
    # config = Config("jira-gantt.ini")
    # print(config.sections)
    # print(config.alt_getter(section='DEFAULT',parameter='Endpoint'))
    # print(config.get_parameter('Endpoint'))
    # print(config.alt_getter().get('DEFAULT','Endpoint'))
    import sys
    sys.exit(0)
