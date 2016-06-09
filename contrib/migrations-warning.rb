DEBUG = false
# Get the commits before the merge
#   ex. heads = ["<latest commit of master>", "<previous commit of master>", ...]
heads = `git reflog -n 2 | awk '{ print $1 }'`.split

# Make sure our revision history has at least 2 entries
if heads.length < 2
    exit 0 
end

# List the file names before and after merge that contain migrations 
#   ex. files = ['core/migrations/blahbal.py']                       

files = `git diff --name-only #{heads[1]} #{heads[0]} | grep migrations/`
if /migrations/.match files then
   default = "\e[0m"
   red = "\e[31m" 
   puts "[#{red}migrations-warning.rb hook#{default}]: New migrations found."

   if DEBUG
       puts "Files found:"
       puts files
   end

   puts "./manage.py migrate"
end
