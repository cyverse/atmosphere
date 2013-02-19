package org.iplantcollaborative.atmo.client.estevewrapper;

import java.io.BufferedReader;
import java.io.Console;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Scanner;
import java.util.Set;


public class AtmoCLv_1_0 {
	private static final String version = "v1.0 - 20110518";
	public static boolean DEBUG = false;
	public static boolean format = false;
	static String username, password;
	static ConsoleEraser consoleEraser;
	static AtmoAPI myatmo;
	static boolean extended;
	static HashMap<String, String> map;	

	public static void runCommand(String command, String[] args) {
		String one, two;
		try {
			/*SANITY CHECKS!*/
			Command cmd = Command.toCommand(command);
			if ( cmd == Command.VOLDET ||
				 cmd == Command.VOLMOUNT) {
				if(args[0] == null || args[1] == null) {
					System.out.println("Expected:"+command+" vol-00000001 /mount/path");
					return;
				}
			} else if ( cmd == Command.APPLAUNCH ||
						cmd == Command.INSTLAUNCH ||
						cmd == Command.VOLDEL ||
						cmd == Command.INSTTERM) {
				if(args[0] == null || args[1] != null) {
					System.out.println("Command expects one parameter");
					return;
				}
			} 
			/*END SANITY CHECKS!*/
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
			//case APPLAUNCH:
			//	AtmoApp aa = myatmo.getApp(args[0]);
			//	System.out.println(myatmo.launchApp(aa.getName(), aa, null));
			//	break;
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
				myatmo.unmountVolume(args[0], args[1], getPassword());
				/*
				if (!myatmo.detachVolume(args[0]))
					System.out.println("Failed to detach volume");
				else {
					command = "echo \"" + AtmoAPI.escape(password) + "\" | sudo -S " + "rm -rf " + args[1];
					if(AtmoCL.DEBUG) {
						System.out.println("CMD2:"+command.replace(password, "<password>"));
					}
					int returned = SystemCall.returnCodePipe(command);
					if(returned == 0 && AtmoCL.DEBUG) {
						System.out.println("Removed directory");
					}
					System.out.println("Detached volume " + args[0] + ".");
				}*/
				break;
			case VOLGET:
				System.out.println(breakup(myatmo.getVolumeList(), false));
				break;
			case VOLMOUNT:
				String instanceid;
				instanceid = getCurrentID();
				if (!myatmo.attachVolume(instanceid, args[0])) {
					System.out.println("Failed to attach volume, try again.");
					System.exit(1);
				}
				if(DEBUG)
					System.out.println("Call to attach volume succeeded.");
				myatmo.getVolumes();
				one = myatmo.getVolume(args[0]).toString();
				two = one;
				while(one.equals(two) == true) {
					myatmo.waitFor(5);//5-second delay to allow volume time to attach before mounting.
					myatmo.getVolumes();
					two = myatmo.getVolume(args[0]).toString();
					if(DEBUG) {
						System.out.println("Before:"+one);
						System.out.println("After:"+two);
					}
				}
				myatmo.mountVolume(map.get("Device"), args[1], getPassword());
				break;
			default:
				System.out.println("Command not recognized");
				break;
			}
		} catch (ArrayIndexOutOfBoundsException ex) {
			System.out.println("ERROR: Not enough arguments given for this command, check usage");
		}
	}

	public static HashMap<String, String> getOptions(String[] args) {

		boolean argParse = false;
		int i = 1;
		
		List<String> argList = (List<String>) Arrays.asList(args);
		HashMap<String, String> opts = new HashMap<String, String>();
		
		opts.put("Device", "/dev/sdb"); //Set default device
		
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
				} else if (a.equals("device")) {
					opts.put("Device", argList.get(++j));
				}
			}
			// Parse Short Options
			else if (a.startsWith("-")) {
				char c = a.toCharArray()[1];
				switch(c) {
				case 'q':
					DEBUG = true;
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
				}
				else {
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
		} catch (Exception e) {;} finally {
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
		AtmoCLv_1_0.username = username;
	}

	public static void setPassword(String password) {
		AtmoCLv_1_0.password = password;
	}

	private static String getPassword() {
		return AtmoCLv_1_0.password;
	}

	public static void setAtmoAPI(AtmoAPI api) {
		AtmoCLv_1_0.myatmo = api;
	}

	public static AtmoAPI getAtmoAPI() {
		return AtmoCLv_1_0.myatmo;
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
		System.out.println(getVersion()+" - iPlant Collaborative");
		System.out.println("Steven \"eSteve\" Gregory - esteve@iplantcollaborative.org");
		System.out.println("Basic Functions:");
		System.out.println("\tvolmount volumeid directory : Mounts a volume to a directory");
		System.out.println("\tvoldet volumeid directory : Unmount volume from directory");
		System.out.println("\tvolget : retrieve list of volumes by volumeid");
		if(extended == true)
			extendedUsage();
		System.out.println("Usage:");
		System.out.println("-u, --user <USERNAME> : Set username to be used for authentication.");
		System.out.println("-p, --password <PASSWORD> : Set password to be used for authentication.");
		System.out.println("-f : Force device format on volmount (Confirmation required)");
		System.out.println("-h, --help : Shows this usage screen");
		System.out.println("-x : Include extended functions in usage screen");
		System.out.println("Example: atmocl [-u username] [-p secret] volmount vol-00000001 /data");
	}
	public static void extendedUsage() {
		System.out.println("Extended Functions:");
		System.out.println("\timgget : retrieve list of instances");
		System.out.println("\tinstget : retrieve list of instances");
		//System.out.println("\tappget : retrieve list of apps");
		System.out.println("\tallget : retrieve list of images, instances and volumes.");//System.out.println("\tallget : retrieve list of apps, images, instances and volumes.");
		System.out.println("\tvolcreate : Creates a new volume");
		System.out.println("\tvoldel volumeid : Delete the selected volume (CAUTION: All data on this volume will be destroyed.)");
		System.out.println("\tinstlaunch imageName : Launch new instance of image");
		//System.out.println("\tapplaunch appName : Launch app");
		System.out.println("Extended Usage:");
		System.out.println("-d, --device <PATH> : Set path to the device to be mounted (Default: /dev/sdb)");
	}

	public static void main(String[] args) {
		// Command Line functions
		if (args.length < 1) {
			usage();
			return;
		}
		Runtime.getRuntime().addShutdownHook(new Thread() {
			public void run() {
				echo(true);
			}
		    });
		map = getOptions(args);
		if(DEBUG) {
			System.out.println("DEBUG MODE ENABLED");
		}
		setUsername(map.get("User"));
		if (username == null)
			getUserInput();
		
		setPassword(map.get("Password"));
		if (password == null)
			getPWInput();
		
		String command = map.get("Command");
		
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
		
		if (DEBUG)
			System.out.println("C:" + command + " P:" + cargs[0] + ", "
					+ cargs[1]);

		// Atmosphere API takes over
		setAtmoAPI(new AtmoAPI());
		
		if (!myatmo.authenticate(username, password)) {
			System.out.println("Failed to authenticate");
			return;
		}
		
		runCommand(command, cargs);
		
		return;
	}
//PRIVATE/ANON/HELPER CLASSES & METHODS \\
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
		if(set == null || set.size() == 0)
			return "";
		String str = "";
		int i = 0;
		for(String s : set) {
			if(addQuote)
				str += ++i+". \""+s+"\"\n";
			else
				str += ++i+". "+s+"\n";
		}
		return str.substring(0,str.length()-1);
	}
	private static boolean askAgain() {
		// TODO Auto-generated method stub
		System.out
				.println("THIS OPERATION WILL DELETE ALL DATA ON THE VOLUME. TYPE 'OK' TO CONTINUE.");
		Scanner kb = new Scanner(System.in);
		String answer = kb.next();
		return (answer.toUpperCase().equals("OK"));
	}
	
	private static String getCurrentID() {
		BufferedReader br = SystemCall.runCommand("atmoinfo");
		String line = null;
		try {
			while((line = br.readLine()) != null) {
			if(line.contains("instance-id")) {
				line = line.substring(line.lastIndexOf('i')).trim();
				return line;
			}
		}
		} catch(Exception e) {;}
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
