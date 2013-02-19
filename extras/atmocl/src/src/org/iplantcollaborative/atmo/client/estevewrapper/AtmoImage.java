package org.iplantcollaborative.atmo.client.estevewrapper;

public class AtmoImage {

	private String name, desc, tags, id, location, owner, state, arch, type,
			ramdisk, kernel;
	private boolean is_public;

	public AtmoImage(String name, String desc, String tags, String id,
			String location, String owner, String state, String arch,
			String type, String ramdisk, String kernel, boolean is_public) {
		super();
		this.name = name;
		this.desc = desc;
		this.tags = tags;
		this.id = id;
		this.location = location;
		this.owner = owner;
		this.state = state;
		this.arch = arch;
		this.type = type;
		this.ramdisk = ramdisk;
		this.kernel = kernel;
		this.is_public = is_public;
	}

	public String getName() {
		return name;
	}

	public String getDesc() {
		return desc;
	}

	public String getTags() {
		return tags;
	}

	public String getId() {
		return id;
	}

	public String getLocation() {
		return location;
	}

	public String getOwner() {
		return owner;
	}

	public String getState() {
		return state;
	}

	public String getArch() {
		return arch;
	}

	public String getType() {
		return type;
	}

	public String getRamdisk() {
		return ramdisk;
	}

	public String getKernel() {
		return kernel;
	}

	public boolean isIs_public() {
		return is_public;
	}

}
