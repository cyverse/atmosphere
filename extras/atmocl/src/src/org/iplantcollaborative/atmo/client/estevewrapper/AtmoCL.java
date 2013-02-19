package org.iplantcollaborative.atmo.client.estevewrapper;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Scanner;
import java.util.Set;
//TODO: Add log support to /var/log/atmo/atmocl.log
//Syntax:
//
public class AtmoCL {
	public static boolean DEBUG = false;
	public static boolean format = false;
	private static final String TAG = "AtmoCL";
	private static final String version = "v1.25 - 20110711";
	private static final String serverselect = "https://atmo-beta.iplantcollaborative.org:443/auth";
	static String username, password;
	static ConsoleEraser consoleEraser;
	static AtmoAPI myatmo;
	static boolean extended;
	static HashMap<String, String> map;

	public static void runCommand(String command, String[] args) {
		String one, two;
		if(DEBUG) {
			System.out.println(command+"-- A="+args);
		}
		try {
			args = testCommandAndParam(command, args);

			switch (Command.toCommand(command)) {
			case ALLGET:
				System.out.println("Images");
				System.out.println(breakup(myatmo.getImageList(), false));
				System.out.println("Instances");
				System.out.println(breakup(myatmo.getInstanceList(), true));
				System.out.println("Volumes");
				System.out.println(breakup(myatmo.getVolumeList(), true));
				break;
			case IMGGET:
				System.out.println(breakup(myatmo.getImageList(), true));
				break;
			case INSTGET:
				System.out.println(breakup(myatmo.getInstanceList(), false));
				break;
			// case APPLAUNCH:
			// AtmoApp aa = myatmo.getApp(args[0]);
			// System.out.println(myatmo.launchApp(aa.getName(), aa, null));
			// break;
			case INSTLAUNCH:
				AtmoImage image = myatmo.getImage(args[0]);
				System.out.println(myatmo.launchInstance(image.getName(),
						image, null));
				break;
			case INSTTERM:
				if (!myatmo.terminateInstance(args[0]))
					System.out.println("Failed to terminate instance.");
				else
					System.out.println("Terminated Instance");
				break;
			case VOLCREATE:
				String newvol = myatmo.createVolume();
				if (newvol == null)
					System.out.println("Failed to create volume");
				else
					System.out.println(newvol);
				break;
			case VOLDEL:
				boolean confirm = askAgain();
				if (confirm)
					if (!myatmo.deleteVolume(args[0]))
						System.out.println("Failed to delete volume");
					else
						System.out.println("Deleted volume " + args[0]);
				else
					System.out.println("Operation Cancelled by User.");
				break;
			case VOLDET:
				/* Step 1: Is unmount necessary? */
				boolean mounted = testUnmount(map.get("Device"), args[1]);
				if (mounted == false) {
					System.out.println(args[1] + " unmounted.");
					/* Mount=No, Detach=? */
					File f = new File(map.get("Device"));
					if (!f.exists()) {
						/* Mount=No, Detach=No */
						System.out.println("Volume " + args[0] + " detached.");
						return;
					}
					/* Mount = No, Detach=Yes */
					if(args[0].length() > 4)
						args[0] = args[0].substring(0,3)+args[0].substring(3).toUpperCase();
					if (!myatmo.detachVolume(args[0])) {
						System.out.println("Failed to detach volume");
						return;
					}
					/* Mount = No, Detach=No. Delete directory prompt */
					if (myatmo.askAgain(args[1])) {
						command = "echo " + AtmoAPI.escape(password)
								+ " | sudo -S " + "rm -rf " + args[1];
						if (AtmoCL.DEBUG) {
							AtmoAPI.logCommand(command,password);
						}
						int returned = SystemCall.returnCodePipe(command);
						if (returned == 0 && AtmoCL.DEBUG) {
							System.out.println("Removed directory");
						}
					} else {
						System.out.println("Detached volume " + args[0] + ".");
					}
				} else {
					/*
					 * Run standard process: Unmount, Detach, ask if directory
					 * should be deleted
					 */
					myatmo.unmountVolume(args[0], args[1], getPassword());
				}
				break;
			case VOLGET:
				System.out.println(breakup(myatmo.getVolumeList(), false));
				break;
			case VOLMOUNT:
				String instanceid;
				boolean status;
				instanceid = getCurrentID();

				String device = map.get("Device");
				if (!device.contains("/dev/")) {
					System.out
							.println("Non-standard device path detected. Path should begin with /dev/");
					return;
				}

				// Testing before call to atmo
				myatmo.getVolumes();
				if (args[0] == null || args[1] == null) {
					System.out
							.println("Could not retrieve parameters. Aborting request.");
					return;
				}
				one = myatmo.getVolume(args[0]).toString();
				two = one; /*
							 * Change in state (one==two) means attach command
							 * successful
							 */

				File f = new File(map.get("Device"));
				/* Attach: No */
				if(args[0].length() > 4)
					args[0] = args[0].substring(0,3)+args[0].substring(3).toUpperCase();
				if (!f.exists()) {
					System.out
							.println("Attaching volume.. This can take some time (10+ Seconds)");
					if (!device.contains("sdb")) {
						device = device.substring(5); // Cuts the '/dev/'
														// portion.
						status = myatmo.attachVolume(instanceid, args[0],
								device);
					} else {
						status = myatmo
								.attachVolume(instanceid, args[0], "sdb");
					}
					if (!status) {
						System.out
								.println("Failed to attach volume, try again.");
						System.exit(1);
					}
					if (DEBUG)
						System.out
								.println("Call to attach volume succeeded. Waiting for response.");
					// Wait for response...
					int time = 0;
					while (one.equals(two) == true && time < 3) {
						time++;
						System.out.println("Waiting.. Attempt #" + time + "/3");
						myatmo.waitFor(10);
						/* After delay, refresh volumes and look for a change */
						myatmo.getVolumes();
						two = myatmo.getVolume(args[0]).toString();
						if (DEBUG) {
							System.out.println("Before:" + one);
							System.out.println("After:" + two);
						}
					}
					if (DEBUG) {
						System.out.println("Attach volume response received.");
					}
					System.out.println("Volume attached");
				}
				/* Attach:Yes, Mount:No */
				myatmo.mountVolume(map.get("Device"), args[1], getPassword());
				break;
			default:
				System.out.println("Command not recognized");
				break;
			}
		} catch (ArrayIndexOutOfBoundsException ex) {
			System.out
					.println("ERROR: Not enough arguments given for this command, check usage");
		}
	}

	private static boolean testUnmount(String device, String volume) {
		String command = "echo " + AtmoAPI.escape(password) + " | sudo -S " + "mount";
		BufferedReader br = SystemCall.runPipeCommand(command);
		String line;
		boolean mounted = false;
		try {
			System.out.println("Checking if " + volume + " is mounted:");
			while ((line = br.readLine()) != null) {
				if (line.contains(device) && line.contains(volume))
					mounted = true;
			}
		} catch (Exception e) {
			;
		}
		return mounted;
	}

	public static HashMap<String, String> getOptions(String[] args) {

		boolean argParse = false;
		int i = 1;

		List<String> argList = (List<String>) Arrays.asList(args);
		HashMap<String, String> opts = new HashMap<String, String>();

		opts.put("Device", "/dev/sdb"); // Set default device

		for (int j = 0; j < args.length; j++) {
			String a = argList.get(j);
			// Parse Long Options
			if (a.startsWith("--")) {
				a = a.substring(2).toLowerCase();
				// --param <ARG>
				if (a.equals("password")) {
					opts.put("Password", argList.get(++j));
				} else if (a.equals("user")) {
					opts.put("User", argList.get(++j));
				} else if (a.equals("help")) {
					usage();
					System.exit(0);
				} else if (a.equals("version")) {
					System.out.println(version);
					System.exit(0);
				} else if (a.equals("device")) {
					opts.put("Device", argList.get(++j));
				}
			}
			// Parse Short Options
			else if (a.startsWith("-")) {
				char c = a.toCharArray()[1];
				switch (c) {
				case 'q':
					DEBUG = true;
					AtmoAPI.DEBUG = true;
					break;
				case 'd':
					opts.put("Device", argList.get(++j));
					break;
				case 'f':
					format = true;
					break;
				case 'p':
					opts.put("Password", argList.get(++j));
					break;
				case 'u':
					opts.put("User", argList.get(++j));
					break;
				case 'h':
					usage();
					System.exit(0);
					break;
				case 'x':
					extended = true;
					usage();
					System.exit(0);
					break;
				}
			}
			// Parse Arguments (Command, Parameter)
			else {
				if (argParse) {
					String argname = "Param" + i++;
					opts.put(argname, argList.get(j));
				} else {
					opts.put("Command", argList.get(j));
					argParse = true;
				}
			}
		}
		return opts;
	}

	public static void getUserInput() {
		Scanner kb = new Scanner(System.in);
		System.out.print("Enter Username: ");
		username = kb.nextLine();
	}

	public static void getPWInput() {
		BufferedReader br = new BufferedReader(new InputStreamReader(System.in));

		try {
			echo(false);
			System.out.print("Enter Password: ");
			password = br.readLine();
			System.out.println();
		} catch (Exception e) {
			;
		} finally {
			echo(true);
		}

	}

	private static String getVersion() {
		// TODO Auto-generated method stub
		return version;
	}

	public static String getUsername() {
		return username;
	}

	public static void setUsername(String username) {
		AtmoCL.username = username;
	}

	public static void setPassword(String password) {
		AtmoCL.password = password;
	}

	private static String getPassword() {
		return AtmoCL.password;
	}

	public static void setAtmoAPI(AtmoAPI api) {
		AtmoCL.myatmo = api;
	}

	public static AtmoAPI getAtmoAPI() {
		return AtmoCL.myatmo;
	}

	public static void usage() {
		System.out
				.println(" ____ ____ ____ ____ ____ ____ ____ ____ ____ ____ ");
		System.out
				.println("||A |||t |||m |||o |||s |||p |||h |||e |||r |||e ||");
		System.out
				.println("||__|||__|||__|||__|||__|||__|||__|||__|||__|||__||");
		System.out
				.println("|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|");
		System.out.println("");
		System.out
				.println(" ____ ____ _________ ____ ____ ____ ____ ____ ____ ____ ____ ____ ____ ____ ");
		System.out
				.println("||B |||y |||       |||C |||o |||m |||m |||a |||n |||d |||L |||i |||n |||e ||");
		System.out
				.println("||__|||__|||_______|||__|||__|||__|||__|||__|||__|||__|||__|||__|||__|||__||");
		System.out
				.println("|/__\\|/__\\|/_______\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|/__\\|");
		System.out.println(getVersion() + " - iPlant Collaborative");
		System.out
				.println("Steven \"eSteve\" Gregory - esteve@iplantcollaborative.org");
		System.out.println("Basic Functions:");
		System.out
				.println("\tvolmount volumeid directory : Mounts a volume to a directory");
		System.out
				.println("\tvoldet volumeid directory : Unmount volume from directory");
		System.out.println("\tvolget : retrieve list of volumes by volumeid");
		if (extended == true)
			extendedUsage();
		System.out.println("Usage:");
		System.out
				.println("-u, --user <USERNAME> : Set username to be used for authentication.");
		System.out
				.println("-p, --password <PASSWORD> : Set password to be used for authentication.");
		System.out
				.println("-f : Force device format on volmount (Confirmation required)");
		System.out.println("-h, --help : Shows this usage screen");
		System.out.println("-x : Include extended functions in usage screen");
		System.out
				.println("Example: atmocl [-u username] [-p secret] volmount vol-00000001 /data");
	}

	public static void extendedUsage() {
		System.out.println("Extended Functions:");
		System.out.println("\timgget : retrieve list of images");
		System.out.println("\tinstget : retrieve list of instances");
		System.out
				.println("\tallget : retrieve list of images, instances and volumes.");
		System.out.println("\tvolcreate : Creates a new volume");
		System.out
				.println("\tvoldel volumeid : Delete the selected volume (CAUTION: All data on this volume will be destroyed.)");
		System.out
				.println("\tinstlaunch imageName : Launch new instance of image");
		System.out.println("Extended Usage:");
		System.out
				.println("-d, --device <PATH> : Set path to the device to be mounted (Default: /dev/sdb)");
	}
	/*
	private static boolean isRoot() {
		String user = null;
		BufferedReader br;
		try {
		br = SystemCall.runCommand("whoami");
		String read = br.readLine();
		if (read != null)
			user = read;
		
		if(user.equals("root"))
			return true;
		else
			return false;
		} catch(Exception e){return false;}
	}
	*/
	private static boolean testSudo() {
		String read;
		BufferedReader br;
		try {
			br = SystemCall.runPipeCommand("echo \"\" | sudo -S whoami");
			read = br.readLine();
			if(read != null && read.equals("root")) {
				return true;
			}
		} catch(Exception e) {;}
		return false;
	}
	
	public static void main(String[] args) {
		// Command Line functions
		if (args.length < 1) {
			usage();
			return;
		}
		/*if(!isRoot()) {
			System.out.println("Must run this command as root. (ex: sudo atmocl ...)");
			return;
		}*/
		Runtime.getRuntime().addShutdownHook(new Thread() {
			public void run() {
				echo(true);
			}
		});
		map = getOptions(args);
		if (DEBUG) {
			System.out.println("DEBUG MODE ENABLED");
		}

		String command = map.get("Command");
		if (command == null) {
			usage();
			return;
		}
		String cargs[] = new String[2];

		String param = map.get("Param1");
		if (param != null)
			cargs[0] = param.replaceAll("_", " ");
		else
			cargs[0] = null;

		param = map.get("Param2");
		if (param != null)
			cargs[1] = param.replaceAll("_", " ");
		else
			cargs[1] = null;
		setAtmoAPI(new AtmoAPI(serverselect));
		if(DEBUG) System.out.println("Checking file credentials..");
		if (!hasFileCredentials(map.get("User"))) {
			setUsername(map.get("User"));
			if (username == null)
				getUserInput();

			setPassword(map.get("Password"));
			if (password == null)
				getPWInput();
			if (!myatmo.authenticate(username, password)) {
				System.out.println("Failed to authenticate");
				return;
			}
			if( createCredentials() )
				System.out.println("Credentials file created.");
		} else {
			//Credentials exist, is the password still cached in sudo?
			if(!testSudo()) {
				//If sudo fails on credential file, ask for password again, reauthenticate and create a new credential file
				getPWInput();
				myatmo.authenticate(username, password);
				if( createCredentials() )
					System.out.println("Credentials file created.");
			} else {
				password = "";
			}
		}
		// Atmosphere API takes over
		runCommand(command, cargs);

		return;
	}

	private static boolean createCredentials() {
		String path = System.getProperty("user.home") + "/.atmocl";
		File f = new File(path);
		String tokendate = "";
		BufferedWriter bw = null;
		try {
			bw = new BufferedWriter(new FileWriter(f));
			tokendate = Long.toString(new Date().getTime());
			bw.write(tokendate);
			bw.newLine();
			bw.write(myatmo.getServer());
			bw.newLine();
			bw.write(myatmo.getToken());
			bw.newLine();
			bw.write(myatmo.getUser());
			bw.newLine();
			bw.write(myatmo.getVersion());
			bw.newLine();
			if(DEBUG) System.out.println("Credentials file created.");
			return true;
		}catch(Exception e) {;}
		finally {
			try {
                if (bw != null) {
                    bw.flush();
                    bw.close();
                }
            } catch (IOException ex) {Log.e(TAG,"Error closing writer.");}
		}
		return false;
	}
	// PRIVATE/ANON/HELPER CLASSES & METHODS \\
	private static boolean hasFileCredentials(String actualUser) {
		String path = System.getProperty("user.home") + "/.atmocl";
		File f = new File(path);
		String tokendate = "";
		try {
			if(f.exists()) {
				BufferedReader br = new BufferedReader(new FileReader(f));
				tokendate = br.readLine();
				Date today = new Date();
				long diff = today.getTime() - Long.parseLong(tokendate);
				if ( (diff / (60 * 60 * 1000)) < 23) {
					if(DEBUG) System.out.println("The tokenfile is active.");
					String server = br.readLine();
					String token = br.readLine();
					String user = br.readLine();
					String version = br.readLine();
					setUsername(user);
					myatmo.setCredentials(server, token, user, version);
					if(DEBUG) System.out.println("Credentials have been set.");
					if(actualUser != null && actualUser.equals(user) == false)
						return false;
					System.out.println("Credentials found for user '"+user+"'");
					return true;
				} else {
					System.out.println("Tokenfile has expired!");
				}
			}
		} catch (Exception e) {if(DEBUG) Log.e(TAG,"File Credentials Parsing Error!");}
		
		return false;
	}

	private static String[] testCommandAndParam(String command, String params[]) {
		Scanner kb = new Scanner(System.in);
		if (params.length != 2) {
			params = new String[2];
		}
		int num, select;
		switch (Command.toCommand(command)) {
		case VOLDEL:
			if (params[0] == null) {
				myatmo.getVolumes();
				ArrayList<String> volumes = new ArrayList<String>(
						myatmo.getVolumeList());
				num = 0;
				for (String s : volumes) {
					System.out.println(++num + ":" + s);
				}
				System.out.println("Select a volume to destroy [1-"
						+ volumes.size() + "]:");
				try {
					select = Integer.parseInt(kb.nextLine());
				} catch (Exception e) {
					select = 0;
				}
				if (select > 0 && select <= volumes.size()) {
					params[0] = volumes.get(select - 1);
				}
			}
			return params;
		case VOLDET:
			if (params[0] == null) {
				myatmo.getVolumes();
				ArrayList<String> volumes = new ArrayList<String>(
						myatmo.getVolumeList());
				num = 0;
				for (String s : volumes) {
					System.out.println(++num + ":" + s);
				}
				System.out.print("Select attached volume [1-" + volumes.size()
						+ "]:");
				try {
					select = Integer.parseInt(kb.nextLine());
				} catch (Exception e) {
					select = 0;
				}
				if (select > 0 && select <= volumes.size()) {
					params[0] = volumes.get(select - 1);
				}
			}
			if (params[1] == null) {
				System.out
						.print("Absolute path to mounted directory [Ex:/mydata]:");
				try {
					params[1] = kb.nextLine();
				} catch (Exception e) {
					params[1] = "";
				}
			}
			return params;
		case VOLMOUNT:
			if (params[0] == null) {
				myatmo.getVolumes();
				ArrayList<String> volumes = new ArrayList<String>(
						myatmo.getVolumeList());
				num = 0;
				for (String s : volumes) {
					System.out.println(++num + ":" + s);
				}
				System.out.print("Select a volume [1-" + volumes.size() + "]:");
				try {
					select = Integer.parseInt(kb.nextLine());
				} catch (Exception e) {
					select = 0;
				}
				if (select > 0 && select <= volumes.size()) {
					params[0] = volumes.get(select - 1);
				}
			}
			if (params[1] == null) {
				System.out
						.print("Absolute path to directory to be mounted [Ex:/mydata]:");
				try {
					params[1] = kb.nextLine();
				} catch (Exception e) {;}
			}
			return params;
		case APPLAUNCH:
			if (params[0] == null) {
				myatmo.getVolumes();
				ArrayList<String> apps = new ArrayList<String>(
						myatmo.getAppList());
				num = 0;
				for (String s : apps) {
					System.out.println(++num + ":" + s);
				}
				System.out.print("Select an app to launch [1-" + apps.size()
						+ "]:");
				try {
					select = Integer.parseInt(kb.nextLine());
				} catch (Exception e) {
					select = 0;
				}
				if (select > 0 && select <= apps.size()) {
					params[0] = apps.get(select - 1);
				}
			}
			return params;
		case INSTLAUNCH:
			if (params[0] == null) {
				myatmo.getVolumes();
				ArrayList<String> images = new ArrayList<String>(
						myatmo.getImageList());
				num = 0;
				for (String s : images) {
					System.out.println(++num + ":" + s);
				}
				System.out.print("Select an image to launch [1-"
						+ images.size() + "]:");
				try {
					select = Integer.parseInt(kb.nextLine());
				} catch (Exception e) {
					select = 0;
				}
				if (select > 0 && select <= images.size()) {
					params[0] = images.get(select - 1);
					System.out.println("Selected Image <" + params[0] + ">");
				}
			}
			return params;
		case INSTTERM:
			if (params[0] == null) {
				myatmo.getVolumes();
				ArrayList<String> instances = new ArrayList<String>(
						myatmo.getInstanceList());
				num = 0;
				for (String s : instances) {
					System.out.println(++num + ":" + s);
				}
				System.out.print("Select an instance to terminate [1-"
						+ instances.size() + "]:");
				try {
					select = Integer.parseInt(kb.nextLine());
				} catch (Exception e) {
					select = 0;
				}
				if (select > 0 && select <= instances.size()) {
					params[0] = instances.get(select - 1);
					System.out.println("Selected Instance <" + params[0] + ">");
				}
			}
			return params;
		default:
			return params;
		}
	}

	public static void echo(boolean on) {
		try {
			String[] cmd = { "/bin/sh", "-c",
					"/bin/stty " + (on ? "echo" : "-echo") + " < /dev/tty" };
			Process p = Runtime.getRuntime().exec(cmd);
			p.waitFor();
		} catch (IOException e) {
		} catch (InterruptedException e) {
		}
	}

	private static String breakup(Set<String> set, boolean addQuote) {
		if (set == null || set.size() == 0)
			return "";
		String str = "";
		int i = 0;
		for (String s : set) {
			if (addQuote)
				str += ++i + ". \"" + s + "\"\n";
			else
				str += ++i + ". " + s + "\n";
		}
		return str.substring(0, str.length() - 1);
	}

	private static boolean askAgain() {
		// TODO Auto-generated method stub
		System.out
				.println("WARNING: THIS OPERATION WILL DELETE ALL DATA ON THE VOLUME. DATA CANNOT BE RESTORED AFTER REMOVAL.\nTYPE 'YES' TO CONTINUE.");
		Scanner kb = new Scanner(System.in);
		String answer = kb.next();
		return (answer.equals("YES"));
	}

	private static String getCurrentID() {
		BufferedReader br = SystemCall.runPipeCommand("/usr/local/bin/atmoinfo");
		String line = null;
		try {
			while ((line = br.readLine()) != null) {
				if (line.contains("instance-id")) {
					line = line.substring(line.lastIndexOf('i')).trim();
					return line;
				}
			}
		} catch (Exception e) {
			;
		}
		return null;
	}

	private enum Command {
		VOLMOUNT, VOLGET, VOLDET, ALLGET, INSTGET, VOLDEL, VOLCREATE, INSTLAUNCH, APPLAUNCH, IMGGET, ERROR, INSTTERM;
		public static Command toCommand(String str) {
			try {
				return valueOf(str.toUpperCase().replace(" ", ""));
			} catch (Exception ex) {
				return ERROR;
			}
		}
	}

	static class ConsoleEraser extends Thread {
		private boolean running = true;

		public void run() {
			while (running) {
				System.out.print("\b ");

			}
		}

		public synchronized void halt() {
			running = false;
		}
	}

}
