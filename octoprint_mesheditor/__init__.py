# coding=utf-8
from __future__ import absolute_import

import flask

import octoprint.plugin
import octoprint.events

class MeshEditorPlugin(octoprint.plugin.SettingsPlugin,
					   octoprint.plugin.AssetPlugin,
					   octoprint.plugin.TemplatePlugin):

	def __init__(self):
		self.wait_g29 = False
		self.mesh_data = []
		self.mesh_size = None
		self.g29_mesh_line = None

	def get_settings_defaults(self):
		return dict(
			grid_size=3,
			mesh_min=-1,
			mesh_max=1,
			mesh_increment=0.05,
			move_offset_x=0,
			move_offset_y=0,
			move_mesh_inset=30,
			move_z_hop=10,
			move_speed_mms=25,
			move_bed_width=230,
			move_bed_length=230
		)

	def get_template_configs(self):
	 	return [
	 		dict(type="settings", custom_bindings=False)
	 	]

	def get_assets(self):
		return dict(
			js=["js/mesheditor.js"],
			css=["css/mesheditor.css"]
		)

	def on_gcode_sending(self, comm, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
		if cmd and cmd in ["G29 S0",'G29 S0 VIRTUAL_DEBUG']:
			self._logger.info("Waiting for mesh...")
			self.wait_g29 = True
			self.mesh_data = None
			if cmd == 'G29 S0 VIRTUAL_DEBUG': return None,
		return None

	def on_gcode_recieved(self, comm, line, *args, **kwargs):
		if not self.wait_g29 or line.strip()=='wait' or line.strip()=='Not SD printing': return line # early out

		if line.strip() == 'Mesh Bed Leveling has no data.':
			self.mesh_data = None
		elif line.strip() in ('Mesh Bed Leveling ON', 'Mesh Bed Leveling OFF'):
			self.g29_mesh_line = -2
			self.mesh_data = []
		elif self.g29_mesh_line is not None and self.g29_mesh_line < 1:
			if 'mesh' in line:
				size = int(line[:line.find('x')])
				
				if size != self._settings.get_int(['grid_size']):
					self._logger.info(f"Mesh size {size} doesn't match plugin setting {self._settings.get_int(['grid_size'])}, changing to match")
					self._settings.set_int(['grid_size'], size)
					self._settings.save(trigger_event=True)
			self.g29_mesh_line += 1
		elif line.strip()!='ok' and self.g29_mesh_line is not None and self.g29_mesh_line > 0:
			try:
				n = int(line[:2])
				if n == self.g29_mesh_line - 1:
					self.mesh_data.append([float(x) for x in line.strip().split(' ')[1:]])
					self.g29_mesh_line += 1
			except ValueError:
				return line
		elif line.strip() == 'ok':
			self._logger.info("Got all mesh data")
			self.wait_g29 = False
			self.g29_mesh_line = None
			self.send_mesh_collected_event()

		return line

	##~~ Softwareupdate hook
	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
		# for details.
		return {
			"mesheditor": {
				"displayName": "Manual Mesh Editor Plugin",
				"displayVersion": self._plugin_version,

				# version check: github repository
				"type": "github_release",
				"user": "The-EG",
				"repo": "OctoPrint-ManualMeshEditor",
				"current": self._plugin_version,

				# update method: pip
				"pip": "https://github.com/The-EG/OctoPrint-ManualMeshEditor/archive/{target_version}.zip",

				# release channels
				"stable_branch": {
					"name": "Stable",
					"branch": "main",
					"comittish": ["main"]
				},
				"prerelease_branches": {
					{
						"name": "Release Candidate",
						"branch": "rc",
						"committish": ["rc", "main"]
					}
				}
			}
		}

	def send_mesh_collected_event(self):
		event = octoprint.events.Events.PLUGIN_MESHEDITOR_MESH_READY
		if self.mesh_data is None:
			data = {'result': 'no mesh'}
		else:
			data = {'result': 'ok', 'data': self.mesh_data, 'grid_size': self._settings.get_int(['grid_size'])}
		self._logger.info('sending mesh data event')
		self._event_bus.fire(event, payload=data)

	def register_custom_events(*args, **kwargs):
		return ["mesh_ready"]



__plugin_name__ = "Manual Mesh Editor"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = MeshEditorPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.gcode.received": __plugin_implementation__.on_gcode_recieved,
		"octoprint.comm.protocol.gcode.sending": __plugin_implementation__.on_gcode_sending,
		"octoprint.events.register_custom_events": __plugin_implementation__.register_custom_events
	}

