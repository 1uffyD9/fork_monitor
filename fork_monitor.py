#!/usr/bin/env python3

import os
import json
import requests
from time import sleep
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)        # take environment variables from .env.

class ForkMonitor:
        ADMIN = os.environ.get('USER')
        TOKEN = os.environ.get('TOKEN')

        def __init__(self, org_name: str, repo: str) -> None:
                self.repo = repo
                self.org_name = org_name
                self.org_members = self.get_members()
                self.fork_tree = {
                                f'{self.org_name}/{self.repo}' : dict()
                        }
                self.fin_output = list()

        def tmp_print(self, response: json):
                print(json.dumps(response, indent=2, sort_keys=True))

        def get_data(self, url: str) -> list:
                """Making request to github APIs for given reletive URL"""
                
                headers = {
                        'User-Agent' : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        'Authorization' : f'token {self.TOKEN}'
                }

                return json.loads(requests.get(f'https://api.github.com/{url}', headers=headers).text)

        def get_members(self) -> list:
                """Get members of a given Organization"""

                org_members = []
                page_number = 1
                while True:
                        # 100 members per page
                        page_members = [collab['login'] for collab in self.get_data(f'orgs/{self.org_name}/members?per_page=100&page={page_number}')]
                        if page_members:
                                org_members.extend(page_members)
                                sleep(0.05)
                        else:
                                # no members in the page
                                break

                        page_number += 1
        
                return org_members


        # ref : https://stackoverflow.com/questions/13687924/setting-a-value-in-a-nested-python-dictionary-given-a-list-of-indices-and-value
        def nested_set(self, dic, keys, value):
                for key in keys[:-1]:
                        dic = dic.setdefault(key, {})
                dic[keys[-1]] = value


        def build_forks_tree(self, dict_in: dict, path=[]) -> None:
                """Build forks tree from a given source dictonary"""

                for index, parent_repo in enumerate(dict_in):

                        forks_list = {}
                        try:
                                # get git forks if repo exist
                                forks_list = {repo['full_name']: dict() for repo in self.get_data(f'repos/{parent_repo}/forks')}
                        except:
                                print("[!] Skipping : directory not found")
                                continue

                        if forks_list:
                                # preparing to enumurate child branch
                                path.append(parent_repo)
                                # if forks exist
                                self.nested_set(self.fork_tree, path, forks_list)
                                yield from self.build_forks_tree(forks_list, path)
                                # go back to parent repo
                                path.pop()


        def get_collab(self, dict_in: dict, path=[]) -> None:
                """Get Collaborators of a given repo"""
 
                for repo in dict_in.keys():
                        path.append(repo)
                        # get assignees for each repo
                        collab = [collab['login'] for collab in self.get_data(f"repos/{repo}/assignees")]
                        #  check for external users
                        diff_members = [member for member in collab if member not in self.org_members]

                        if diff_members:
                                yield repo, path, diff_members

                        yield from self.get_collab(dict_in[repo], path)
                        path.pop()


        def generate_final_out(self, repo: str, path: list, dif_collab: list) -> None:
                self.fin_output.append(
                        {
                                "repository" : repo,
                                "forked_chain" : list(path),
                                "external_users" : dif_collab
                        }
                )

        def main(self):

                # get source repos' forks
                print("[!] Generating fork tree....")
                for _ in self.build_forks_tree(self.fork_tree) : pass
                self.tmp_print(self.fork_tree)

                print("[!] Checking repos for external users...")
                for repo, path, diff_colab in self.get_collab(self.fork_tree):
                        self.generate_final_out(repo, path, diff_colab)

                self.tmp_print(self.fin_output)

if __name__ == "__main__":
        org_name = os.environ.get('ORGNAME')
        repo = os.environ.get('REPO')
        
        fm = ForkMonitor(org_name, repo)
        fm.main()
