from html.parser import HTMLParser


class MenuParser(HTMLParser):
    """Parser of the page menu bar to extract the necessary pages.

    Examples:

        >>> parser = MenuParser()
        >>> parser.feed(html)
        >>> pages_to_visit = parser.hrefs
    """

    def __init__(self):
        super().__init__()
        self.in_target_div = False
        self.div_depth = 0

        self.ul_found = False
        self.ul_depth = 0

        self.li_depth = 0
        self.capture_a = False

        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        # Find target div
        if tag == "div" and attrs.get("id") == "top_sub_menu_83557":
            self.in_target_div = True
            self.div_depth = 1
            return

        if self.in_target_div:
            if tag == "div":
                self.div_depth += 1

            # First UL inside the div
            if tag == "ul" and not self.ul_found:
                self.ul_found = True
                self.ul_depth = 1
                return

        if self.ul_found:
            if tag == "ul":
                self.ul_depth += 1

            if tag == "li" and self.ul_depth == 1:
                self.li_depth = 1
                return

            if self.li_depth == 1 and tag == "a":
                href = attrs.get("href")
                if href:
                    self.hrefs.append(href)
                self.capture_a = True

    def handle_endtag(self, tag):
        if self.in_target_div and tag == "div":
            self.div_depth -= 1
            if self.div_depth == 0:
                self.in_target_div = False

        if self.ul_found and tag == "ul":
            self.ul_depth -= 1

        if self.li_depth and tag == "li":
            self.li_depth = 0
            self.capture_a = False


class PaginationParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_pagination_nav = False
        self.in_page_ul = False
        self.pages = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "nav" and "pagination" in attrs.get("class", ""):
            self.in_pagination_nav = True

        elif self.in_pagination_nav and tag == "ul":
            if "page-list" in attrs.get("class", ""):
                self.in_page_ul = True

        elif self.in_page_ul and tag == "a":
            href = attrs.get("href", "")
            if "page=" in href:
                try:
                    page = int(href.split("page=")[1].split("&")[0])
                    self.pages.append(page)
                except ValueError:
                    pass

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_pagination_nav = False
            self.in_page_ul = False
