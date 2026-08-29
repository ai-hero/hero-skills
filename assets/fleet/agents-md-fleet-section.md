## Fleet

This repo is one checkout in a fleet: sibling repos in the folder above it,
mapped by that folder's `FLEET.md` (`hero-skills:fleet`). The map is local and
unversioned, so clone this repo beside the others and run
`hero-skills:fleet review`. The host port this dev stack publishes is claimed
in that map, not chosen here: take the next free port there first, then set
it in every place this repo names it (compose defaults, health checks).
Any hero skill run from the fleet folder fans out to the repos you pick.
