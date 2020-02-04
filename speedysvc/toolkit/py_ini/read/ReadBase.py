from collections import OrderedDict


class ReadBase:
    def read_D(self, path):
        with open(path, 'r', errors='replace', encoding='utf-8') as f:
            return self.__read_D(f)

    def __read_D(self, f):
        """
        Parse a .ini file with [sections] and python variables
        SECURITY NOTE: ASSUMES TRUSTED INPUT!
        """
        DRtn = OrderedDict()
        LSection = None
        LSections = []
        section_mode = True

        for line in f:
            s_line = line.strip()
            #print s_line

            if not s_line:
                continue
            elif line.startswith('#') or not s_line:
                # A comment/blank line - ignore
                continue

            end_of_header = (
                s_line.split('#')[0].strip().rstrip(':') and
                s_line.split('#')[0].strip().rstrip(':')[-1] == ']'
            )

            if (
                (
                    s_line.startswith('["') or
                    s_line.startswith("['") or
                    s_line.startswith('[#')
                ) or (
                    s_line.startswith('[') and
                    end_of_header
                )
            ):
                # Start of a new section
                DRtn.update(
                    self.get_D_sections(LSections, LSection)
                )
                LSections = [line]
                LSection = []

                if end_of_header:
                    section_mode = False
                else:
                    section_mode = True

            elif section_mode:
                if LSections and end_of_header:
                    LSections.append(line)
                    section_mode = False

                else:
                    LSections.append(line)

            else:
                # Add to section data
                LSection.append(line)
                assert LSections

        DRtn.update(
            self.get_D_sections(LSections, LSection)
        )
        return DRtn

    def get_D_sections(self, LSections, LSection):
        #print LSections, LSection
        D = {}
        if LSections:
            if any(i for i in ''.join(LSections) if i in "\"'"):
                # Multiple sections stored as a python list, e.g.
                # ['section 1', 'section 2']
                #print LSections, LSection
                for section in eval(
                    '\n'.join(i.strip() for i in LSections)
                ):
                    D[section] = self.process_section(
                        section,
                        ''.join(LSection)
                    )
            else:
                # A single section stored inside brackets, e.g.
                # [section 1]
                assert len(LSections) == 1
                section = LSections[0].strip().strip(':')[1:-1].strip()

                D[section] = self.process_section(
                    section,
                    ''.join(LSection)
                )
        return D

    def process_section(self, section, data):
        raise NotImplementedError
