package org.iplantcollaborative.atmo.client.estevewrapper;

public class AtmoVolume {
	String id, tags, attach_data_device, status, description, name, create_time, attach_data_attach_time, snapshot_id, attach_data_instance_id;
	int num, size;

	public AtmoVolume(String id, String tags, String attach_data_device,
			String status, String description, String name, String create_time,
			String attach_data_attach_time, String snapshot_id,
			String attach_data_instance_id, int num, int size) {
		super();
		this.id = id;
		this.tags = tags;
		this.attach_data_device = attach_data_device;
		this.status = status;
		this.description = description;
		this.name = name;
		this.create_time = create_time;
		this.attach_data_attach_time = attach_data_attach_time;
		this.snapshot_id = snapshot_id;
		this.attach_data_instance_id = attach_data_instance_id;
		this.num = num;
		this.size = size;
	}
	public String getID() {
		return id;
	}
	public void setId(String id) {
		this.id = id;
	}
	public String getTags() {
		return tags;
	}
	public void setTags(String tags) {
		this.tags = tags;
	}
	public String getAttach_data_device() {
		return attach_data_device;
	}
	public void setAttach_data_device(String attach_data_device) {
		this.attach_data_device = attach_data_device;
	}
	public String getStatus() {
		return status;
	}
	public void setStatus(String status) {
		this.status = status;
	}
	public String getDescription() {
		return description;
	}
	public void setDescription(String description) {
		this.description = description;
	}
	public String getName() {
		return name;
	}
	public void setName(String name) {
		this.name = name;
	}
	public String getCreate_time() {
		return create_time;
	}
	public void setCreate_time(String create_time) {
		this.create_time = create_time;
	}
	public String getAttach_data_attach_time() {
		return attach_data_attach_time;
	}
	public void setAttach_data_attach_time(String attach_data_attach_time) {
		this.attach_data_attach_time = attach_data_attach_time;
	}
	public String getSnapshot_id() {
		return snapshot_id;
	}
	public void setSnapshot_id(String snapshot_id) {
		this.snapshot_id = snapshot_id;
	}
	public String getAttach_data_instance_id() {
		return attach_data_instance_id;
	}
	public void setAttach_data_instance_id(String attach_data_instance_id) {
		this.attach_data_instance_id = attach_data_instance_id;
	}
	public int getNum() {
		return num;
	}
	public void setNum(int num) {
		this.num = num;
	}
	public int getSize() {
		return size;
	}
	public void setSize(int size) {
		this.size = size;
	}
	@Override
	public String toString() {
		return "AtmoVolume [id=" + id + ", tags=" + tags
				+ ", attach_data_device=" + attach_data_device + ", status="
				+ status + ", description=" + description + ", name=" + name
				+ ", create_time=" + create_time + ", attach_data_attach_time="
				+ attach_data_attach_time + ", snapshot_id=" + snapshot_id
				+ ", attach_data_instance_id=" + attach_data_instance_id
				+ ", num=" + num + ", size=" + size + "]";
	}


}
