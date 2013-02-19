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

public class AtmoCLv_0_1 {
	private static final boolean DEBUG = false;

	private enum Command {
		ATTACHVOLUME, APPLIST, CREATEKEYPAIR, CREATEVOLUME, DELETEVOLUME, DETACHVOLUME, ERROR, GETINSTANCEID, IMAGELIST, INSTANCELIST, KEYPAIRLIST, LAUNCHAPP, LAUNCHINSTANCE, RUNNINGINSTANCES, TERMINATEINSTANCE, VOLUMELIST;
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

	static String username, password;
	static ConsoleEraser consoleEraser;
	static AtmoAPI myatmo;

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
		System.out.println("iPlant Collaborative");
		System.out
				.println("Steven \"eSteve\" Gregory - esteve@iplantcollaborative.org");
		System.out.println("COMMANDS:");
		System.out.println("\tattachVolume instanceid volumeid");
		System.out.println("\tcreateVolume");
		// System.out.println("\tdeleteVolume volumeid");
		System.out.println("\tdetachVolume volumeid");
		System.out.println("\tvolumeList");
		
		System.out.println("\tinstanceList");
		System.out.println("\trunningInstances");
		System.out.println("\tgetInstanceId instanceName");
		System.out.println("\tlaunchInstance imageName");
		System.out.println("\tterminateInstance imageName");
		
		System.out.println("\timageList");
		
		// System.out.println("\tcreateKeyPair keypairName");
		// System.out.println("\tkeypairList");
		
		System.out.println("\tlaunchApp appName");
		System.out.println("USAGE:");
		System.out.println("-u, --user <USERNAME> : Set username to be used for authentication.");
		System.out.println("-p, --password <PASSWORD> : Set password to be used for authentication. (Optional)");
		System.out.println("-h, --help : Shows this usage screen");
		System.out.println("Example: atmocl -u username -p secret launchapp appname");
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
			System.out.print("enter password: ");
			password = br.readLine();
			System.out.println();
		} catch (Exception e) {
			;
		} finally {
			echo(true);
		}

	}

	public static String getUsername() {
		return username;
	}

	public static void setUsername(String username) {
		AtmoCLv_0_1.username = username;
	}

	public static void setPassword(String password) {
		AtmoCLv_0_1.password = password;
	}

	private static String getPassword() {
		return AtmoCLv_0_1.password;
	}

	public static void setAtmoAPI(AtmoAPI api) {
		AtmoCLv_0_1.myatmo = api;
	}

	public static AtmoAPI getAtmoAPI() {
		return AtmoCLv_0_1.myatmo;
	}

	public static void chooseCommand(String command, String[] args) {
		try {
			switch (Command.toCommand(command)) {
			case APPLIST:
				System.out.println(myatmo.getAppList());
				break;
			case ATTACHVOLUME:
				if (!myatmo.attachVolume(args[0], args[1]))
					System.out.println("Failed to attach volume");
				else
					System.out.println("Attached volume " + args[1]
							+ " to instance " + args[0] + ".");
				break;
			case CREATEKEYPAIR:
				System.out.println("UNSUPPORTED METHOD");// myatmo.creteKeyPair(args[3]);
				break;
			case CREATEVOLUME:
				String newvol = myatmo.createVolume();
				if (newvol == null)
					System.out.println("Failed to create volume");
				else
					System.out.println(newvol);
				break;
			case DELETEVOLUME:
				boolean confirm = askAgain();
				if (confirm)
					if (!myatmo.deleteVolume(args[0]))
						System.out.println("Failed to delete volume");
					else
						System.out.println("Deleted volume " + args[1] + ".");
				else
					System.out.println("Operation Cancelled by User.");
				break;
			case DETACHVOLUME:
				if (!myatmo.detachVolume(args[0]))
					System.out.println("Failed to detach volume");
				else
					System.out.println("Detached volume " + args[1] + ".");
				break;
			case GETINSTANCEID:
				AtmoInstance myinst = myatmo.getInstance(args[0]);
				if (myinst != null)
					System.out.println(myinst.getInstance_id());
				break;
			case IMAGELIST:
				System.out.println(myatmo.getImageList());
				break;
			case INSTANCELIST:
				System.out.println(myatmo.getInstanceList());
				break;
			case KEYPAIRLIST:
				System.out.println("UNSUPPORTED METHOD");// System.out.println(myatmo.getKeyPairList());
				break;
			case LAUNCHAPP:
				AtmoApp aa = myatmo.getApp(args[0]);
				System.out.println(myatmo.launchApp(aa.getName(), aa, null));
				break;
			case LAUNCHINSTANCE:
				AtmoImage image = myatmo.getImage(args[0]);
				System.out.println(myatmo.launchInstance(image.getName(),
						image, null));
				break;
			case TERMINATEINSTANCE:
				if (!myatmo.terminateInstance(args[0]))
					System.out.println("Failed to terminate instance.");
				else
					System.out.println("Terminated Instance");
				break;
			case VOLUMELIST:
				System.out.println(myatmo.getVolumeList());
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

	private static boolean askAgain() {
		// TODO Auto-generated method stub
		System.out
				.println("THIS OPERATION WILL DELETE ALL DATA ON THE VOLUME. TYPE 'OK' TO CONTINUE.");
		Scanner kb = new Scanner(System.in);
		String answer = kb.next();
		return (answer.toUpperCase().equals("OK"));
	}

	public static HashMap<String, String> getOptions(String[] args) {

		HashMap<String, String> opts = new HashMap<String, String>();
		String manip;
		boolean argParse = false;
		int i = 1;
		List<String> argList = (List<String>) Arrays.asList(args);
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
				}
			}
			// Parse Short Options
			else if (a.startsWith("-")) {
				a = a.substring(1).toLowerCase();
				if (a.equals("p")) {
					opts.put("Password", argList.get(++j));
				} else if (a.equals("u")) {
					opts.put("User", argList.get(++j));
				} else if (a.equals("h")) {
					usage();
					System.exit(0);
				}
			}
			// Parse Non-Options (Command, Parameter)
			else {
				if (argParse) {
					String argname = "Param" + i++;
					opts.put(argname, argList.get(j));
				}
				// --command <CMD>
				else {
					opts.put("Command", argList.get(j));
					argParse = true;
				}
			}
		}
		return opts;
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

	public static void main(String[] args) {
		// Command Line functions
		if (args.length < 2) {
			System.out.println(args.length);
			usage();
			return;
		}
		HashMap<String, String> map = getOptions(args);
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
		chooseCommand(command, cargs);
		return;
	}

}
