#!/usr/bin/perl -w -T
use strict;
use CGI qw(:standard);
#set this for testing purposes only
#use CGI::Carp qw(fatalsToBrowser);
use File::Temp;

#some security-settings
$CGI::POST_MAX = 1024 * 100;
$ENV{'PATH'} = '/bin:/usr/bin:/usr/local/bin';

#gather all mibs in smipath into @mibnames
my $smipath = "/usr/share/apps/snmpb/mibs;/usr/share/apps/snmpb/pibs";
my @smidirs = split(/:/,$smipath);
my @mibnames;
foreach my $dir (@smidirs) {
    opendir(MIBDIR,$dir);
    my @entries = grep !/^\.\.?\z/, readdir(MIBDIR);
    closedir(MIBDIR);
    @mibnames = (@mibnames, @entries);
}

if (param()) {
    #params present.
    my @options;
    my $localfh;
    my $localfn;
    my @mibs = param('mibs');
    my $width = param('width');
    my $height = param('height');

    #parse options and add safe strings to the options-array
    if (param('deprobs')) {
	if (param('deprobs') eq "deprecated") {
	    @options = (@options, "--svg-show-deprecated");
	} elsif (param('deprobs') eq "obsolete") {
	    @options = (@options, "--svg-show-depr-obsolete");
	}
    }

    if (param('static')) {
	@options = (@options, "--svg-static-output");
    }

    if ($width =~ /(\d+)/) {
	if ($1 <= 2147483647) {
	    @options = (@options, "--svg-width=$1");
	}
    }
    if ($height =~ /(\d+)/) {
	if ($1 <= 2147483647) {
	    @options = (@options, "--svg-height=$1");
	}
    }

    #parse selected MIBs
    foreach my $mibname (@mibnames) {
	foreach my $mib (@mibs) {
	    if ($mibname eq $mib) {
		$mibname =~ /([\w\-]+)/;
		@options = (@options, "$1");
	    }
	}
    }

    #handle file upload
    if (param('uploadmib')) {
	my $remotefh = upload('uploadmib');
	($localfh, $localfn)
	    = File::Temp->tempfile('tempMIBXXXX', DIR => '/tmp', UNLINK => 1)
		or die "Error opening outfile\n";
	while (<$remotefh>) {
	    print $localfh $_;
	}
	close $remotefh;
	close $localfh;
	@options = (@options, $localfn);
    }

    #call smidump
    my $res = open (SMIDUMP, "-|");
    die "Couldn't open pipe to subprocess" unless defined($res);
    exec "/usr/local/bin/smidump",'-u','-f','svg',@options
	or die "Couldn't exec smidump" if $res == 0;
    my @svg = <SMIDUMP>;
    close (SMIDUMP);

    #serve svg
    my $svglength = @svg;
    if ($svglength eq 0) {
	print header;
	print start_html("MIB to SVG");
	print h2("Sorry, smidump output contained no data.");
	print end_html;
    } else {
	#FIXME - or + ?
	print header(-TYPE => "image/svg-xml");
	print "@svg";
    }

} else {
    #no params present
    #send form
    print header;
    print start_html("MIB to SVG");
    print h2("Generate a SVG Diagram from MIB Modules");
    print start_multipart_form();

    print p("select one or more MIBs: ", scrolling_list(
	-NAME => "mibs",
	-VALUES => [@mibnames],
	-SIZE => 10,
	-MULTIPLE => 1,
    ));

    print p("or upload a MIB: ", filefield(
	-NAME => "uploadmib"
    ));

    print p("diagram width: ", textfield(
	-NAME => "width",
	-DEFAULT => "1100"
    ));
    print p("diagram height: ", textfield(
	-NAME => "height",
	-DEFAULT => "700"
    ));

    print p(radio_group(
	-NAME => "deprobs",
	-VALUES => [ qw(none deprecated obsolete) ],
	-LINEBREAK => 1,
	-LABELS => {
	    none => "show only current objects",
	    deprecated => "show current and deprecated objects",
	    obsolete => "show all objects",
	},
    ));

    print p(checkbox(
	-NAME => "static",
	-LABEL => "generate a smaller, non-interactive SVG diagram",
    ));

    print p(submit("generate SVG"), reset("reset form"));
    print end_form;
    print end_html;
}
