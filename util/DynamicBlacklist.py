import ipaddress    # woah, this is a default module? neat.
import requests     # to get the microsoft azure ip ranges
import re    # to search through the html to find the file (because there's currently no API to automate getting ranges)
import json         # to parse the file once it's been downloaded

"""
This file contains classes and methods to manage acquiring, parsing, and updating a possibly dynamic list of IP ranges
that Guardian needs to be aware of. Such ranges include R* / T2 official IPs, as well as IPs that can be used for
miscellaneous R* Services, such as Microsoft Azure.
"""


class ScrapeError(BaseException):
    """ Could not scrape the HTML for data for some reason. """


# TODO: Find an API we can use to get these ranges dynamically. If necessary, these ones can be used as a fallback,
#  as I don't think these ranges change often.
# https://whois.ipip.net/AS202021
T2_EU = {"185.56.64.0/24", "185.56.64.0/22", "185.56.65.0/24", "185.56.66.0/24", "185.56.67.0/24"}

# https://whois.ipip.net/AS46555
T2_US = {"104.255.104.0/24", "104.255.104.0/22", "104.255.105.0/24", "104.255.106.0/24", "104.255.107.0/24",
         "192.81.240.0/24", "192.81.240.0/22", "192.81.241.0/24", "192.81.242.0/24", "192.81.243.0/24",
         "192.81.244.0/24", "192.81.244.0/22", "192.81.245.0/24", "192.81.246.0/24", "192.81.247.0/24",
         "198.133.210.0/24"}

# This URL should return information about the most up-to-date JSON file containing Azure IP ranges.
# Microsoft claims that a new file is published every 7 days, and that any new IPs will not be used for another 7 days.
# Note that we could also possibly manually generate the URL if necessary.
# I'm not very good at web development so idk what the best practice is for this lol
AZURE_GET_PUBLIC_CLOUD_URL = "https://www.microsoft.com/en-us/download/confirmation.aspx?id=56519"
# The regex pattern to find download files on the page.
MICROSOFT_DOWNLOAD_REGEX = re.compile('https://download.microsoft.com/download[^"]*[.]json')


def get_azure_ip_ranges_download(page_to_search=AZURE_GET_PUBLIC_CLOUD_URL):
    """
    Finds the URL to the most recent JSON file. I looked it up and yes, apparently, there is no actual API that allows
    requesting the most up-to-date ranges. We have to download the human-readable page, then parse / search through the
    HTML response to find the link.

    This method is *meant* to be comprehensive and robust enough to not break if Microsoft changes the HTML content of
    their pages. When this code was written, the download file occurred multiple times in the HTML page, but it was the
    only URL to match the regular expression.

    If multiple possibly valid files were found on the page, they will all be returned.
    """

    # Get the actual page.
    try:
        response = requests.get(page_to_search)
        response.raise_for_status()  # If there was an error code, raise it.
        #if response.status_code != 200:
        #    raise ScrapeError("URL to scrape returned " + str(response.status_code) + " instead of 200.", response)

        # Search through the HTML for all download.microsoft.com JSON files.
        files = re.findall(MICROSOFT_DOWNLOAD_REGEX, str(response.content))
        if files is None:
            raise ScrapeError("Did not find any valid download URLs while searching the page.", response)

        files = list(set(files))  # Removes any duplicate finds.
        return files

    except (ScrapeError, requests.exceptions.RequestException) as e:
        """ For whatever reason, we couldn't find a file to download. We can attempt to generate the URL manually. """
        # TODO: Figure out what times (and timezones) Microsoft publish their IP ranges at.
        raise e


def parse_azure_ip_ranges(url_to_json_file):
    """
    Given a Microsoft Azure IP .JSON file, parses the file and returns an array of strings of CIDR ranges
    that may be used by R* Services.
    """
    response = requests.get(url_to_json_file)
    response.raise_for_status()  # Can't handle anything here. If we can't download the file, it's game over.
    # TODO: Using reverse_search_ip_in_azure() indicates that R* Services use the generic 'AzureCloud' category.
    #  A bit boring but to be expected and hey, at least they're actually in the file.
    #  So, need to get the address ranges (they're CIDR) from that category and return a set of IPs to compare against.


def get_all_ips_from_cidr(ip_in_cidr_notation):
    ips = set()
    ip_range = ipaddress.IPv4Network(ip_in_cidr_notation)
    for ip in ip_range:
        ips.add(str(ip))

    return ips


def get_all_ips_from_cidr_array(array_of_ip_in_cidr_notation):
    ips = set()
    for ip_range in array_of_ip_in_cidr_notation:
        ips = ips.union(get_all_ips_from_cidr(ip_range))

    return ips


# Tries to find places where an IP occurs in the azure info.
def reverse_search_ip_in_azure(ip, azure_info_json):
    search = []  # where categories will be added
    categories = azure_info_json['values']
    # categories is a list of dictionaries
    for cat in categories:
        ranges = cat['properties']['addressPrefixes']
        for str_cidr in ranges:
            try:
                cidr = ipaddress.IPv4Network(str_cidr)
                if ipaddress.IPv4Address(ip) in cidr:
                    search.append(cat)
            except ipaddress.AddressValueError:
                pass  # not an IPv4 CIDR range. couldn't find an "is IPv4" / "is CIDR" function
    return search


if __name__ == "__main__":
    print(get_all_ips_from_cidr("185.56.64.0/24"))
    print(len(get_all_ips_from_cidr_array(["185.56.64.0/24", "185.56.64.0/22"])))
    print(get_azure_ip_ranges_download())
