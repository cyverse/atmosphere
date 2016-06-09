DEBUG = false

# Get the commits before the merge
#   ex. heads = ["<latest commit of master>", "<previous commit of master>", ...]
heads = `git reflog -n 2 | awk '{ print $1 }'`.split

# Make sure our revision history has at least 2 entries
if heads.length < 2
    exit 0 
end

files = `git diff --name-only #{heads[1]} #{heads[0]} | grep requirements.txt`
diffFiles = `git diff --name-only #{heads[1]} #{heads[0]} | grep requirements.txt | tr "\n" " "`
if diffFiles then
    default = "\e[0m"
    red = "\e[31m" 
    puts "[#{red}requirements-warning.rb hook#{default}]: New python requirements."
    puts "pip install #{diffFiles}"

    if DEBUG then
        # Print the diff with 0 lines of context
        puts `git diff -U0 #{heads[1]} #{heads[0]} -- #{diffFiles}`
    end
end
