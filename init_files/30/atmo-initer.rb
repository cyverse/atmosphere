#!/usr/bin/ruby
require 'net/http'
require 'open3'
require 'digest/sha1'
require 'open-uri'
require 'rubygems'
require 'json'
require 'logger'

$log = Logger.new('/var/log/atmo/atmo_init.log')
$this_version = '2012.09.20.001'
$version = '29'
$resource_url = 'http://128.196.172.136:8773/latest/meta-data/'
$instance_info_hash = Hash.new

def hashCheck( url, remotehash, file )
  $log.debug("hashCheck #{file}")

  if url == ""
    $log.error("Invalid URL parse -- expects http://www.example.com/path/to/file")
    return false
  end
  $log.debug("\tchecking file")
  if File.file?(file)
    if not File.readable?(file)
      $log.error("Local file permission error, missing Read permissions")
      return false
    end
    if not File.writable?(file)
      $log.error("Local file permission error, missing Write permissions")
      return false
    end
    localhash = Digest::SHA1.hexdigest(File.read(file))
    if localhash == remotehash
      $log.debug("\tsame file, hashCheck done")
      return true
    end
  end
  #Download the File
  begin
    $log.debug("\tdownloading file from #{url}")
    fileContents = open(url).read
    hashthis = Digest::SHA1.hexdigest(fileContents)
    if hashthis != remotehash
      $log.error("Hash argument does not match Remote file")
    end
  rescue Exception=>e
    $log.error("Cannot download remote file #{url}")
    return false
  end
  #Write to local file
  begin
    $log.debug("\twriting remove file to local file")
    writeOut = open(file, "wb")
    writeOut.write(fileContents)
    writeOut.close
  rescue Exception=>e
    $log.error("Cannot write to local file #{file}")
    return false
  end
  return true
end

def main(args)
  atmo_srv_download_prefix = JSON.parse(args)['atmosphere']['server']
  atmo_init_append = """
arg = #{args}
main(arg)
"""
  hashCheck("#{atmo_srv_download_prefix}/init_files/#{$version}/atmo-init-full.py", "aff25779245b62936023a42ecafdfc5ef7cd2199", "/usr/sbin/atmo_init_full")

  IO.popen("/bin/chmod a+x /usr/sbin/atmo_init_full") { |f| }
  open("/usr/sbin/atmo_init_full", "a") do |f|
    f.puts atmo_init_append
  end
  stdin, stdout, stderr, wait_thr = Open3.popen3("/usr/sbin/atmo_init_full", args)
  $log.debug "stdout: #{stdout.gets.to_s}"
  $log.debug "stderr: #{stderr.gets.to_s}"
  stdin.close
  stdout.close
  stderr.close
end
