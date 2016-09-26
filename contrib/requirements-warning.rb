# Get the commits before the merge
#   ex. heads = ["<latest commit of master>", "<previous commit of master>", ...]
heads = `git reflog -n 2 | awk '{ print $1 }'`.split

# Make sure our revision history has at least 2 entries
if heads.length < 2
    exit 0
end

# Get all files that changed
files = `git diff --name-only #{heads[1]} #{heads[0]}`

# If (dev_)requrements.txt changed, alert the user!
if /requirements.txt/ =~ files
    default = "\e[0m"
    red = "\e[31m"
    puts "[#{red}requirements-warning.rb hook#{default}]: New python requirements."
    puts "pip install *requirements.txt"
end
