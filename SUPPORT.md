# Help with Updates and Common Issues

If you encounter the error **"Branches have diverged. Manual intervention may be required."** while trying to update, please use the following command to reset your branch in case of a complete history rewrite:

```sh
git fetch origin
git reset --hard origin/<branch_name>
```

Make sure to replace `<branch_name>` with the name of your current branch.

Before executing this command, ensure you have backed up any important changes, as this will discard local commits that are not in the remote branch.

If you continue to experience issues after following these steps, please create a new issue with details of the problem you are facing.
