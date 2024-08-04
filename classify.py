#!/usr/local/python/current/bin/python3

import os
import multiprocessing
import subprocess
import uuid
import pygit2
import yaml
from github import Github, Auth
from github.Repository import Repository

gh_token = os.environ.get('GH_TOKEN')
gh_org = os.environ.get('GH_ORG')
gh_team = os.environ.get('GH_TEAM')
target_gh_org = os.environ.get('TARGET_GH_ORG')
random_uuid = str(uuid.uuid4())
os.mkdir(f'/tmp/{random_uuid}')
auth = Auth.Token(gh_token)
credentials = pygit2.UserPass('IreshMM', gh_token)
callbacks = pygit2.RemoteCallbacks(credentials=credentials)

g = Github(auth = auth)

class ClassifiedRepo:
    def __init__(self, repo: Repository, classification: str):
        self.repo = repo
        self.classification = classification

    def get_classification(self):
        return self.classification

def get_org_repos(org_name: str) -> list:
    org = g.get_organization(org_name)
    return list(org.get_repos())

def get_team_repos(team_name: str, gh_org: str) -> list:
    print(f"Getting repos for team {team_name} in org {gh_org}")
    org = g.get_organization(gh_org)
    team = org.get_team_by_slug(team_name)
    return list(team.get_repos())

def clone_repo(repo: Repository) -> str:
    clone_path = f'/tmp/{random_uuid}/{repo.name}'
    checkout_branch = 'dev_protected'
    if not checkout_branch in [ branch.name for branch in list(repo.get_branches()) ]:
        checkout_branch = None
    pygit2.clone_repository(repo.clone_url, clone_path, callbacks=callbacks, depth=1, checkout_branch=checkout_branch)
    return clone_path

def determine_repo_type(clone_path: str) -> str:
    print(f"Determining repo type for {clone_path}")
    result = subprocess.run(['./repo_type.sh', clone_path], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8').strip()

def classify_repo(repo: Repository) -> ClassifiedRepo:
    print(f"Classifying repo {repo.name}")
    clone_path = clone_repo(repo)
    repo_type = determine_repo_type(clone_path)
    return ClassifiedRepo(repo, repo_type)

def filter_repos(repos: list[Repository], repo_type: str) -> list:
    return [repo for repo in repos if repo.get_classification() == repo_type]

def write_to_yaml(repos: list[Repository], repo_type: str):
    list_of_repos = [
                        {'name': repo.repo.name,
                         'url': repo.repo.clone_url,
                         'target_name': regularize_repo_name(repo.repo.name),
                         'target_url': f'https://github.com/{target_gh_org}/{regularize_repo_name(repo.repo.name)}.git'
                        } 
                         for repo in repos
                    ]
    with open(f'/tmp/{random_uuid}/{repo_type}.yaml', 'w') as f:
        yaml.dump(list_of_repos, f, default_flow_style=False)

def regularize_repo_name(repo_name: str) -> str:
    return repo_name.lower().replace('_', '-').replace('sb-', '')

def __main__():
    pool = multiprocessing.Pool(50)
    classifications = pool.map(classify_repo, get_team_repos(gh_team, gh_org))
    repo_types = set([repo.get_classification() for repo in classifications])
    for repo_type in repo_types:
        filtered_repos = filter_repos(classifications, repo_type)
        write_to_yaml(filtered_repos, repo_type)

if __name__ == '__main__':
    __main__()