#!/usr/bin/python
#
# Copyright 2014-2015 Timothy Sutton
#   Adapted for the GitHub downloads API endpoint by
#   Justin L R Graham <jlgraham@ku.edu>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""See docstring for GitHubDownloadsInfoProvider class"""

# Disabling warnings for env members and imports that only affect recipe-
# specific processors.
#pylint: disable=e1101,f0401

import re
import urllib2

import autopkglib.github
from autopkglib import Processor, ProcessorError

__all__ = ["GitHubDownloadsInfoProvider"]

class GitHubDownloadsInfoProvider(Processor):
    #pylint: disable=missing-docstring
    description = ("Get metadata from the latest download from a GitHub project "
                   "using the GitHub Downloads API.")
    input_variables = {
        "download_regex": {
            "required": False,
            "description": ("If set, return only a download that "
                            "matches this regex.")
        },
        "version_regex": {
            "required": True,
            "description": ("Use this regex to determine the version, "
                            "the first match group is used.")
        },
        "github_repo": {
            "required": True,
            "description": ("Name of a GitHub user and repo, ie. "
                            "'MagerValp/AutoDMG'")
        },
    }
    output_variables = {
        "url": {
            "description": ("URL for the first asset found for the project's "
                            "latest download.")
        },
        "version": {
            "description": ("Version info parsed, parsed from the "
                            "download's name.")
        },
    }

    __doc__ = description


    def get_downloads(self, repo):
        """Return a list of downloads dicts for a given GitHub repo. repo must
        be of the form 'user/repo'"""
        #pylint: disable=no-self-use
        downloads = None
        github = autopkglib.github.GitHubSession()
        downloads_uri = "/repos/%s/downloads" % repo
        try:
            (downloads, status) = github.call_api(downloads_uri)
        # Catch a 404
        except urllib2.HTTPError as err:
            raise ProcessorError("GitHub API returned an error: '%s'." % err)
        if status != 200:
            raise ProcessorError(
                "Unexpected GitHub API status code %s." % status)

        if not downloads:
            raise ProcessorError("No downloads found for repo '%s'" % repo)

        return downloads


    def select_download(self, downloads, regex):
        selected = None
        for download in downloads:
            if selected:
                break

            if not regex:
                selected = download
                break
            else:
                if re.match(regex, download["name"]):
                    self.output("Matched regex %s among download(s): %s" % (
                        regex,
                        ", ".join(x["name"] for x in downloads)))
                    selected = download
                    break

        if not selected:
            raise ProcessorError(
                "No downloads were found that satisfy the criteria.")

        self.selected_download = download

        version_match = re.match(self.env["version_regex"], download["name"])
        if version_match:
            self.env["version"] = version_match.group(1)
            self.env["version"] = self.env["version"].replace('-', '_')
        else:
            raise ProcessorError(
                "Unable to determine package version using regex %s on %s." % (
                    self.env["version_regex"],
                    download["name"]))


    def main(self):
        # Get our list of downloads
        downloads = self.get_downloads(self.env["github_repo"])
        from operator import itemgetter

        def loose_compare(this, that):
            from distutils.version import LooseVersion
            return cmp(LooseVersion(this), LooseVersion(that))

        downloads = sorted(downloads,
                          key=itemgetter("created_at"),
                          cmp=loose_compare,
                          reverse=True)

        # Store the first eligible download
        self.select_download(downloads, self.env.get("download_regex"))

        # Record the url
        self.env["url"] = self.selected_download["html_url"]


if __name__ == "__main__":
    PROCESSOR = GitHubDownloadsInfoProvider()
    PROCESSOR.execute_shell()
