#!/usr/bin/ruby
require 'net/http'
require 'open3'
require 'digest/sha1'
require 'open-uri'
require 'rubygems'
require 'json'
require 'logger'

$log = Logger.new('/var/log/atmo/atmo_init.log')
$this_version = '2014.01.29'
$version = 'v1'
$instance_info_hash = Hash.new

def hashCheck( url, remotehash, file )
  if url == ""
    $log.error("Invalid URL parse -- expects http://www.e.com/path")
    return false
  end
  if File.file?(file)
    if not File.readable?(file)
      return false
    end
    if not File.writable?(file)
      return false
    end
    filehash = Digest::SHA1.hexdigest(File.read(file))
    if filehash == remotehash
      return true
    end
  end
  begin
    $log.debug("\tdownloading #{url}")
    contents = open(url).read
    hashthis = Digest::SHA1.hexdigest(contents)
    if hashthis != remotehash
      $log.error("Hash argument does not match")
    end
  rescue Exception=>e
    $log.error("Cannot download#{url}")
    return false
  end
  begin
    writeOut = open(file, "wb")
    writeOut.write(contents)
    writeOut.close
    $log.debug("\tfile #{file} saved")
  rescue Exception=>e
    $log.error("Cannot write #{file}")
    return false
  end
  return true
end

def main(args)
  args_dict = JSON.parse(args)
  atmo_server = args_dict['atmosphere']['server']
  atmo_service_type = args_dict['atmosphere']['servicename']
  atmo_token = args_dict['atmosphere']['token']
  atmo_name = args_dict['atmosphere']['name']
  atmo_userid = args_dict['atmosphere']['userid']
  atmo_instance_url = args_dict['atmosphere']['instance_service_url']
  atmo_vnc_license = args_dict['atmosphere']['vnc_license']
  password = args_dict['atmosphere']['root_password']
  
  hashCheck("#{atmo_server}/init_files/#{$version}/atmo_init_full.py", "16a59379e7efb15040dade15c596863b8d8d9dd7", "/usr/sbin/atmo_init_full")
  IO.popen("/bin/chmod a+x /usr/sbin/atmo_init_full") { |f| }
  stdin, stdout, stderr, wait_thr = Open3.popen3('/usr/sbin/atmo_init_full --service_type="%s" --token="%s" --name="%s" --server="%s" --service_url="%s" --user_id="%s" --vnc_license="%s" --root_password="%s"' % [atmo_service_type, atmo_token, atmo_name, atmo_server, atmo_instance_url, atmo_userid, atmo_vnc_license, password])
  $log.debug stdout.read
  $log.debug stderr.read
  stdin.close
  stdout.close
  stderr.close
end
