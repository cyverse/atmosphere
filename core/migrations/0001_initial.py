# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Identity'
        db.create_table('identity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('provider', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Provider'])),
        ))
        db.send_create_signal('core', ['Identity'])

        # Adding model 'Credential'
        db.create_table('credential', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('identity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Identity'])),
        ))
        db.send_create_signal('core', ['Credential'])

        # Adding model 'Quota'
        db.create_table('quota', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('cpu', self.gf('django.db.models.fields.IntegerField')(default=2, null=True, blank=True)),
            ('memory', self.gf('django.db.models.fields.IntegerField')(default=4, null=True, blank=True)),
            ('storage', self.gf('django.db.models.fields.IntegerField')(default=50, null=True, blank=True)),
            ('storage_count', self.gf('django.db.models.fields.IntegerField')(default=2, null=True, blank=True)),
        ))
        db.send_create_signal('core', ['Quota'])

        # Adding model 'ProviderType'
        db.create_table('provider_type', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 18, 0, 0))),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['ProviderType'])

        # Adding model 'ProviderSize'
        db.create_table('provider_size', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('cpu', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('ram', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('disk', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['ProviderSize'])

        # Adding model 'Provider'
        db.create_table('provider', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ProviderType'])),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['Provider'])

        # Adding model 'Script'
        db.create_table('script', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('version', self.gf('django.db.models.fields.IntegerField')()),
            ('location', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
        ))
        db.send_create_signal('core', ['Script'])

        # Adding model 'Package'
        db.create_table('package', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('sha1sum', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('location', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
        ))
        db.send_create_signal('core', ['Package'])

        # Adding M2M table for field scripts on 'Package'
        db.create_table('package_scripts', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('package', models.ForeignKey(orm['core.package'], null=False)),
            ('script', models.ForeignKey(orm['core.script'], null=False))
        ))
        db.create_unique('package_scripts', ['package_id', 'script_id'])

        # Adding model 'Tag'
        db.create_table('tag', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.SlugField')(max_length=128)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal('core', ['Tag'])

        # Adding model 'Machine'
        db.create_table('machine', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('icon', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('init_package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Package'], null=True, blank=True)),
            ('private', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('featured', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 18, 0, 0))),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['Machine'])

        # Adding M2M table for field tags on 'Machine'
        db.create_table('machine_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('machine', models.ForeignKey(orm['core.machine'], null=False)),
            ('tag', models.ForeignKey(orm['core.tag'], null=False))
        ))
        db.create_unique('machine_tags', ['machine_id', 'tag_id'])

        # Adding model 'ProviderMachine'
        db.create_table('provider_machine', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('provider', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Provider'])),
            ('machine', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Machine'])),
            ('identifier', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('core', ['ProviderMachine'])

        # Adding model 'Instance'
        db.create_table('instance', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=36, null=True, blank=True)),
            ('provider_machine', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ProviderMachine'])),
            ('provider_alias', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('ip_address', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39, null=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 18, 0, 0))),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('core', ['Instance'])

        # Adding M2M table for field tags on 'Instance'
        db.create_table('instance_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('instance', models.ForeignKey(orm['core.instance'], null=False)),
            ('tag', models.ForeignKey(orm['core.tag'], null=False))
        ))
        db.create_unique('instance_tags', ['instance_id', 'tag_id'])

        # Adding model 'Group'
        db.create_table('group', (
            ('group_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.Group'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('core', ['Group'])

        # Adding M2M table for field leaders on 'Group'
        db.create_table('group_leaders', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('group', models.ForeignKey(orm['core.group'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('group_leaders', ['group_id', 'user_id'])

        # Adding model 'ProviderMembership'
        db.create_table('provider_membership', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('provider', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Provider'])),
            ('member', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Group'])),
        ))
        db.send_create_signal('core', ['ProviderMembership'])

        # Adding model 'IdentityMembership'
        db.create_table('identity_membership', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Identity'])),
            ('member', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Group'])),
            ('quota', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Quota'])),
        ))
        db.send_create_signal('core', ['IdentityMembership'])

        # Adding model 'InstanceMembership'
        db.create_table('instance_membership', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('instance', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Instance'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Group'])),
        ))
        db.send_create_signal('core', ['InstanceMembership'])

        # Adding model 'MachineMembership'
        db.create_table('machine_membership', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('machine', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Machine'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Group'])),
        ))
        db.send_create_signal('core', ['MachineMembership'])

        # Adding model 'UserProfile'
        db.create_table('user_profile', (
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True, primary_key=True)),
            ('send_emails', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('quick_launch', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('vnc_resolution', self.gf('django.db.models.fields.CharField')(default='800x600', max_length=255)),
            ('default_size', self.gf('django.db.models.fields.CharField')(default='m1.small', max_length=255)),
            ('background', self.gf('django.db.models.fields.CharField')(default='default', max_length=255)),
            ('icon_set', self.gf('django.db.models.fields.CharField')(default='default', max_length=255)),
            ('selected_identity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Identity'], null=True, blank=True)),
        ))
        db.send_create_signal('core', ['UserProfile'])

        # Adding model 'MachineRequest'
        db.create_table('machine_request', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('instance', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Instance'])),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('parent_machine', self.gf('django.db.models.fields.related.ForeignKey')(related_name='ancestor_machine', to=orm['core.ProviderMachine'])),
            ('iplant_sys_files', self.gf('django.db.models.fields.TextField')()),
            ('installed_software', self.gf('django.db.models.fields.TextField')()),
            ('exclude_files', self.gf('django.db.models.fields.TextField')()),
            ('access_list', self.gf('django.db.models.fields.TextField')()),
            ('new_machine_provider', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Provider'])),
            ('new_machine_name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('new_machine_owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('new_machine_visibility', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('new_machine_description', self.gf('django.db.models.fields.TextField')()),
            ('new_machine_tags', self.gf('django.db.models.fields.TextField')()),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 18, 0, 0))),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('new_machine', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='created_machine', null=True, to=orm['core.ProviderMachine'])),
        ))
        db.send_create_signal('core', ['MachineRequest'])

        # Adding model 'MaintenanceRecord'
        db.create_table('maintenance_record', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('disable_login', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('core', ['MaintenanceRecord'])

        # Adding model 'NodeController'
        db.create_table('node_controller', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('provider', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Provider'])),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('private_ssh_key', self.gf('django.db.models.fields.TextField')()),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 18, 0, 0))),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['NodeController'])

        # Adding model 'Size'
        db.create_table('size', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('provider', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Provider'])),
            ('cpu', self.gf('django.db.models.fields.IntegerField')()),
            ('disk', self.gf('django.db.models.fields.IntegerField')()),
            ('mem', self.gf('django.db.models.fields.IntegerField')()),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 18, 0, 0))),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['Size'])

        # Adding model 'Volume'
        db.create_table('volume', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('provider', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Provider'])),
            ('size', self.gf('django.db.models.fields.IntegerField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 2, 18, 0, 0))),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['Volume'])


    def backwards(self, orm):
        # Deleting model 'Identity'
        db.delete_table('identity')

        # Deleting model 'Credential'
        db.delete_table('credential')

        # Deleting model 'Quota'
        db.delete_table('quota')

        # Deleting model 'ProviderType'
        db.delete_table('provider_type')

        # Deleting model 'ProviderSize'
        db.delete_table('provider_size')

        # Deleting model 'Provider'
        db.delete_table('provider')

        # Deleting model 'Script'
        db.delete_table('script')

        # Deleting model 'Package'
        db.delete_table('package')

        # Removing M2M table for field scripts on 'Package'
        db.delete_table('package_scripts')

        # Deleting model 'Tag'
        db.delete_table('tag')

        # Deleting model 'Machine'
        db.delete_table('machine')

        # Removing M2M table for field tags on 'Machine'
        db.delete_table('machine_tags')

        # Deleting model 'ProviderMachine'
        db.delete_table('provider_machine')

        # Deleting model 'Instance'
        db.delete_table('instance')

        # Removing M2M table for field tags on 'Instance'
        db.delete_table('instance_tags')

        # Deleting model 'Group'
        db.delete_table('group')

        # Removing M2M table for field leaders on 'Group'
        db.delete_table('group_leaders')

        # Deleting model 'ProviderMembership'
        db.delete_table('provider_membership')

        # Deleting model 'IdentityMembership'
        db.delete_table('identity_membership')

        # Deleting model 'InstanceMembership'
        db.delete_table('instance_membership')

        # Deleting model 'MachineMembership'
        db.delete_table('machine_membership')

        # Deleting model 'UserProfile'
        db.delete_table('user_profile')

        # Deleting model 'MachineRequest'
        db.delete_table('machine_request')

        # Deleting model 'MaintenanceRecord'
        db.delete_table('maintenance_record')

        # Deleting model 'NodeController'
        db.delete_table('node_controller')

        # Deleting model 'Size'
        db.delete_table('size')

        # Deleting model 'Volume'
        db.delete_table('volume')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'core.credential': {
            'Meta': {'object_name': 'Credential', 'db_table': "'credential'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Identity']"}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'core.group': {
            'Meta': {'object_name': 'Group', 'db_table': "'group'", '_ormbases': ['auth.Group']},
            'group_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.Group']", 'unique': 'True', 'primary_key': 'True'}),
            'identities': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Identity']", 'through': "orm['core.IdentityMembership']", 'symmetrical': 'False'}),
            'instances': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Instance']", 'through': "orm['core.InstanceMembership']", 'symmetrical': 'False'}),
            'leaders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'machines': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Machine']", 'through': "orm['core.MachineMembership']", 'symmetrical': 'False'}),
            'providers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Provider']", 'through': "orm['core.ProviderMembership']", 'symmetrical': 'False'})
        },
        'core.identity': {
            'Meta': {'object_name': 'Identity', 'db_table': "'identity'"},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Provider']"})
        },
        'core.identitymembership': {
            'Meta': {'object_name': 'IdentityMembership', 'db_table': "'identity_membership'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Identity']"}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Group']"}),
            'quota': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Quota']"})
        },
        'core.instance': {
            'Meta': {'object_name': 'Instance', 'db_table': "'instance'"},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'provider_alias': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'provider_machine': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ProviderMachine']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 18, 0, 0)'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Tag']", 'symmetrical': 'False'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'})
        },
        'core.instancemembership': {
            'Meta': {'object_name': 'InstanceMembership', 'db_table': "'instance_membership'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Instance']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Group']"})
        },
        'core.machine': {
            'Meta': {'object_name': 'Machine', 'db_table': "'machine'"},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'init_package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Package']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'providers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Provider']", 'through': "orm['core.ProviderMachine']", 'symmetrical': 'False'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 18, 0, 0)'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Tag']", 'symmetrical': 'False'})
        },
        'core.machinemembership': {
            'Meta': {'object_name': 'MachineMembership', 'db_table': "'machine_membership'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'machine': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Machine']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Group']"})
        },
        'core.machinerequest': {
            'Meta': {'object_name': 'MachineRequest', 'db_table': "'machine_request'"},
            'access_list': ('django.db.models.fields.TextField', [], {}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'exclude_files': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'installed_software': ('django.db.models.fields.TextField', [], {}),
            'instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Instance']"}),
            'iplant_sys_files': ('django.db.models.fields.TextField', [], {}),
            'new_machine': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'created_machine'", 'null': 'True', 'to': "orm['core.ProviderMachine']"}),
            'new_machine_description': ('django.db.models.fields.TextField', [], {}),
            'new_machine_name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'new_machine_owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'new_machine_provider': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Provider']"}),
            'new_machine_tags': ('django.db.models.fields.TextField', [], {}),
            'new_machine_visibility': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'parent_machine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_machine'", 'to': "orm['core.ProviderMachine']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 18, 0, 0)'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'core.maintenancerecord': {
            'Meta': {'object_name': 'MaintenanceRecord', 'db_table': "'maintenance_record'"},
            'disable_login': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'core.nodecontroller': {
            'Meta': {'object_name': 'NodeController', 'db_table': "'node_controller'"},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'private_ssh_key': ('django.db.models.fields.TextField', [], {}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Provider']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 18, 0, 0)'})
        },
        'core.package': {
            'Meta': {'object_name': 'Package', 'db_table': "'package'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'scripts': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Script']", 'symmetrical': 'False'}),
            'sha1sum': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'core.provider': {
            'Meta': {'object_name': 'Provider', 'db_table': "'provider'"},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ProviderType']"})
        },
        'core.providermachine': {
            'Meta': {'object_name': 'ProviderMachine', 'db_table': "'provider_machine'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'machine': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Machine']"}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Provider']"})
        },
        'core.providermembership': {
            'Meta': {'object_name': 'ProviderMembership', 'db_table': "'provider_membership'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Group']"}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Provider']"})
        },
        'core.providersize': {
            'Meta': {'object_name': 'ProviderSize', 'db_table': "'provider_size'"},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'cpu': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'disk': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'ram': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'core.providertype': {
            'Meta': {'object_name': 'ProviderType', 'db_table': "'provider_type'"},
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 18, 0, 0)'})
        },
        'core.quota': {
            'Meta': {'object_name': 'Quota', 'db_table': "'quota'"},
            'cpu': ('django.db.models.fields.IntegerField', [], {'default': '2', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memory': ('django.db.models.fields.IntegerField', [], {'default': '4', 'null': 'True', 'blank': 'True'}),
            'storage': ('django.db.models.fields.IntegerField', [], {'default': '50', 'null': 'True', 'blank': 'True'}),
            'storage_count': ('django.db.models.fields.IntegerField', [], {'default': '2', 'null': 'True', 'blank': 'True'})
        },
        'core.script': {
            'Meta': {'object_name': 'Script', 'db_table': "'script'"},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'version': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.size': {
            'Meta': {'object_name': 'Size', 'db_table': "'size'"},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'cpu': ('django.db.models.fields.IntegerField', [], {}),
            'disk': ('django.db.models.fields.IntegerField', [], {}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mem': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Provider']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 18, 0, 0)'})
        },
        'core.tag': {
            'Meta': {'object_name': 'Tag', 'db_table': "'tag'"},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '128'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'core.userprofile': {
            'Meta': {'object_name': 'UserProfile', 'db_table': "'user_profile'"},
            'background': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '255'}),
            'default_size': ('django.db.models.fields.CharField', [], {'default': "'m1.small'", 'max_length': '255'}),
            'icon_set': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '255'}),
            'quick_launch': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'selected_identity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Identity']", 'null': 'True', 'blank': 'True'}),
            'send_emails': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'vnc_resolution': ('django.db.models.fields.CharField', [], {'default': "'800x600'", 'max_length': '255'})
        },
        'core.volume': {
            'Meta': {'object_name': 'Volume', 'db_table': "'volume'"},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Provider']"}),
            'size': ('django.db.models.fields.IntegerField', [], {}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 18, 0, 0)'})
        }
    }

    complete_apps = ['core']