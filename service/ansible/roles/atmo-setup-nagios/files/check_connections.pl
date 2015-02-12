#!/usr/bin/perl

#
# By Jorge Schrauwen 2011
# http://blackdot.be
#

# imports
use strict;
use Nagios::Plugin;

# variables
my $nagios;
my $established = 0;
my $listeners = 0;
my $waiting = 0;
my $netstat;

# plugin setup
$nagios = Nagios::Plugin->new(
        plugin          => 'check_connections',
        shortname       => 'CONNECTIONS',
        version         => '1.0',
        usage           => 'Usage: %s -w <warn> -c <crit>',
        blurb           => 'This plugin checks the established connections.',
        license         => 'This nagios plugin is free software, and comes with ABSOLUTELY no WARRANTY!'
);

$nagios->add_arg(spec => 'warning|w=s',
                          help => "Warning threshold",
                          required => 1);
$nagios->add_arg(spec => 'critical|c=s',
                          help => "Critical threshold",
                          required => 1);

# main
$nagios->getopts;

$netstat = `which netstat 2> /dev/null`;
chop $netstat;
if ( ! -e $netstat ) {
        $nagios->nagios_die("Could not find netstat binary!");
}

foreach my $entry (split("\n", `$netstat -wtun`)) {
        if ( $entry =~ m/ESTABLISHED/ ) { $established++; }
        if ( $entry =~ m/TIME_WAIT/ )   { $waiting++; }
}

foreach my $entry (split("\n", `$netstat -wltun`)) {
        if ( $entry =~ m/LISTEN/ ) { $listeners++; }
}

my $code = $nagios->check_threshold(
        check => $established,
        warning => $nagios->opts->warning,
        critical => $nagios->opts->critical,
);

my $message = sprintf("There are %d established connections.", $established);

# output
$nagios->add_perfdata(
        label => "established",
        value => $established,
);
$nagios->add_perfdata(
        label => "waiting",
        value => $waiting,
);
$nagios->add_perfdata(
        label => "listeners",
        value => $listeners,
);
$nagios->nagios_exit($code, $message);

