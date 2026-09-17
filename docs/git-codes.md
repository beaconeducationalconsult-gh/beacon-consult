git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/beaconeducationalconsult-gh/beacon-consult.git
git push -u origin main

## ##########################################################################################
## ##########################################################################################

git add .
git commit -m "describe your change"
git push origin main

## ##########################################################################################
## ##########################################################################################

cd beacon-consult
git fetch origin
git switch --track origin/arena/01a0af88-beacon-consult