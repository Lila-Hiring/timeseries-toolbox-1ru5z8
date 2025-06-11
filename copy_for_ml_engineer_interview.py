import subprocess
import os
import random
import string
import argparse
from github import Github


def _change_visibility(repo, make_public: bool):
    """
    Change the visibility of a repository to either public or private.

    Args:
        repo: Repository object to modify
        make_public: Boolean flag to make repository public (default: False)
    """

    if make_public:
        repo.edit(private=False)
        print(f"Repository {repo.name} is now public")
    else:
        repo.edit(private=True)
        print(f"Repository {repo.name} is now private")


def copy_repo(args, gh: Github):
    """
    Copy a repository from the source organization to the target organization.

    Args:
        args: Namespace object containing:
            - source_repo: Name of the source repository
            - new_repo: Name for the new repository (optional)
            - source_org: Source organization name (default: lichess-org)
            - target_org: Target organization name (default: lila-hiring)
    """
    # Replace these with your actual values
    source_repo_name = args.source_repo
    if source_repo_name != "inventory-management-exercise":
        if input("Are you sure you want to copy repo named {source_repo_name} to Lila Hiring? (y/N): ").lower() != "y":
            print("Aborting")
            return
    source_repo_path = f"git@github.com:fl97inc/{source_repo_name}.git"
    new_org = args.org

    new_repo_name = f"{source_repo_name}-{''.join(random.choices(
        string.ascii_letters + string.digits, k=6))}"

    # Clean up any existing directory first
    if os.path.exists(source_repo_name + ".git"):
        subprocess.run(["rm", "-rf", source_repo_name + ".git"])

    # Clone the source repo
    subprocess.run(["git", "clone", "--mirror", source_repo_path])

    # Change directory into the cloned repository
    os.chdir(source_repo_name + ".git")

    try:
        # Create a new repository in the new organization
        org = gh.get_organization(new_org)
        new_repo = org.create_repo(new_repo_name, private=True)

        # Get source repository to copy PRs from
        source_repo = gh.get_repo(f"fl97inc/{source_repo_name}")

        # Get all open pull requests from source repo
        open_prs = source_repo.get_pulls(state='open')

        # Set the new remote URL
        new_remote_url = f"git@github.com:{new_org}/{new_repo_name}.git"
        subprocess.run(["git", "remote", "set-url", "origin", new_remote_url])

        # Push all refs to the new repository (simplified push command)
        subprocess.run(["git", "push", "--mirror"])

        # Create pull requests matching the source repo's open PRs
        for pr in open_prs:
            try:
                new_repo.create_pull(
                    title=pr.title,
                    body=pr.body,
                    head=f"{new_org}:{pr.head.ref}",  # Specify the full ref path
                    base=pr.base.ref
                )
            except Exception as e:
                print(f"Warning: Could not create PR {pr.title}: {e}")
                continue

        if args.public:
            _change_visibility(new_repo, args.public)
        print("Copy complete!")
        # Clean up by removing the cloned repository
    finally:
        os.chdir("..")  # Move back to parent directory
        subprocess.run(["rm", "-rf", source_repo_name + ".git"])


def list_repos(args, gh: Github):
    """
    List all repositories in the specified organization.

    Args:
        args: Namespace object containing:
            - org: Organization name to list repositories from (default: lila-hiring)
            - filter: Optional string to filter repository names
    """
    org = gh.get_organization(args.org)
    for repo in org.get_repos():
        print(f"- {repo.name} ({repo.html_url})")


def delete_repo(args, gh: Github):
    """
    Delete a repository from the specified organization.

    Args:
        args: Namespace object containing:
            - repo_name: Name of the repository to delete
            - org: Organization name (default: lila-hiring)
    """
    org = gh.get_organization(args.org)
    try:
        repo = org.get_repo(args.repo_name)
        if args.force or input(f"Are you sure you want to delete {args.repo_name}? (y/N): ").lower() == 'y':
            repo.delete()
            print(f"Repository {args.repo_name} has been deleted.")
        else:
            print("Deletion cancelled.")
    except Exception as e:
        print(f"Error deleting repository: {e}")


def change_visibility(args, gh: Github):
    """
    Change the visibility of a repository to either public or private.

    Args:
        args: Namespace object containing:
            - repo_name: Name of the repository to modif
            - org: Organization name (default: lila-hiring)
            - public: Boolean flag to make repository public (default: False)
    """
    org = gh.get_organization(args.org)
    try:
        repo = org.get_repo(args.repo_name)
        _change_visibility(repo, args.public)
    except Exception as e:
        print(f"Error changing repository visibility: {e}")


def main():
    """
    Main function that sets up the command-line interface and handles command routing.
    Supports commands for copying, listing, deleting repositories and changing their visibility.
    """
    parser = argparse.ArgumentParser(description="GitHub repository management tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Copy command
    copy_parser = subparsers.add_parser('copy', help='Copy a repository')
    copy_parser.add_argument('--public', action='store_true', help='Make repository public (default is private)')
    copy_parser.add_argument('--source_repo', help='Name of the source repository', default='inventory-management-exercise')
    copy_parser.add_argument('--org', default='lila-hiring', help='Target organization name')

    # List command
    list_parser = subparsers.add_parser('list', help='List repositories in organization')
    list_parser.add_argument('--org', default='lila-hiring', help='Organization name')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a repository')
    delete_parser.add_argument('repo_name', help='Name of the repository to delete')
    delete_parser.add_argument('--org', default='lila-hiring', help='Organization name')
    delete_parser.add_argument('--force', '-f', action='store_true', help='Force delete without confirmation')

    # Visibility command
    visibility_parser = subparsers.add_parser('visibility', help='Change repository visibility')
    visibility_parser.add_argument('repo_name', help='Name of the repository')
    visibility_parser.add_argument('--org', default='lila-hiring', help='Organization name')
    visibility_parser.add_argument('--public', action='store_true', help='Make repository public (default is private)')

    args = parser.parse_args()
    gh = Github(os.environ["GITHUB_PAT"])

    if args.command == 'copy':
        copy_repo(args, gh)
    elif args.command == 'list':
        list_repos(args, gh)
    elif args.command == 'delete':
        delete_repo(args, gh)
    elif args.command == 'visibility':
        change_visibility(args, gh)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
