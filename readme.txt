# Move dir to /opt/
$ mv metrics-forwarder/ /opt/

# Make daemon script executable
$ chmod +x /opt/metrics-forwarder/forwarderd.sh

# Create link to init.d daemon system 
$ ln -s /opt/metrics-forwarder/forwarderd.sh /etc/init.d/forwarderd

# Start the service
$ /etc/init.d/forwarderd start

# Stop the service
$ /etc/init.d/forwarderd stop

# Adding system startup link
$ update-rc.d forwarderd defaults

# Removing any system startup link
$ update-rc.d -f forwarderd remove
