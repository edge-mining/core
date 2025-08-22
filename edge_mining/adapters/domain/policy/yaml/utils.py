"""Collection of utility functions for YAML handling in policy management."""

from yaml import SafeDumper


class CustomDumper(SafeDumper):
    """Custom YAML dumper for better formatting."""

    def increase_indent(self, flow=False, indentless=False):
        """
        Forces array elements to be indented correctly, causing them to always be
        indented relative to their parent container, rather than aligned with the
        root element.
        """
        return super(CustomDumper, self).increase_indent(flow, False)

    def represent_list(self, data):
        """
        Checks whether a list contains only primitive values (int, float, str)
        and in that case uses the flow style (square brackets), otherwise
        uses the normal block style.
        """
        # Check if this list should be in flow style (for value arrays)
        if len(data) > 0 and all(isinstance(item, (int, float, str)) for item in data):
            return self.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)
        return self.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=False)


# Add the custom list representer
CustomDumper.add_representer(list, CustomDumper.represent_list)
