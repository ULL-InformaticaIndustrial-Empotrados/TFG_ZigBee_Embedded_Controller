Detalles de construcción actualizados
=====================================

Snap's base
-----------

**1. Instalación de Snapcraft**

	$ sudo apt-get install snapcraft

**2. Construcción del [Gadget](armhf-snaps) para PandaBoard**

	$ cd armhf-snaps
	$ make MACHINE=panda

**3. Construcción del [Kernel](linux-armhf-snap) para PandaBoard**

	$ cd linux-armhf-snap
	$ snapcraft login
	$ sudo snapcraft --target-armhf

Compilación en máquina ARM
--------------------------

**1. Preparación de la máquina**

	$ sudo snap install classic --devmode --beta
	$ sudo classic
	$ sudo apt-get update

------------------------------------------------------------------------------
**NOTA**

En la versión actual de *classic* snap, apt-key no es capaz de verificar la firma de los repositorios. Es necesario añadir la siguiente configuración de *apt_conf* para permitir repositorios sin autenticar:

	$ echo 'APT::Get::AllowUnauthenticated "true";' | sudo tee /etc/apt/apt.conf.d/99allow-unauthenticated

------------------------------------------------------------------------------

**2. Instalación de requisitos**

	$ sudo apt-get install snapcraft git-core build-essential

**3. Descarga del código fuente**

	$ git clone https://github.com/ULL-InformaticaIndustrial-Empotrados/TFG_ZigBee_Embedded_Controller.git

**4. Construcción de snaps**

	$ cd domoticz-snap
	$ snapcraft --no-parallel-build

	$ cd mir-server-snap
	$ snapcraft --no-parallel-build

	$ cd mir-kiosk-browser-snap
	$ snapcraft --no-parallel-build

Imágen resultado
----------------
**1. Generación**

	$ sudo snap install --channel=edge --devmode ubuntu-image
	$ UBUNTU_IMAGE_SKIP_COPY_UNVERIFIED_MODEL=1 ubuntu-image image.assertion \
                       -c edge \
                       -o panda-xbee.img \
                       --extra-snaps armhf-snaps/panda_*.snap \
                       --extra-snaps linux-panda-snap/linux-panda_*.snap \
                       --extra-snaps mir-server/mir-server_*.snap \
                       --extra-snaps mir-kiosk-browser/mir-kiosk-browser_*.snap


**2. Volcado en la tarjeta de memoria**

	$ sudo dd if=panda-xbee.img bs=4k of=/dev/sdX

(Sustituir */dev/sdX* por el dispositivo correspondiente a la tarjeta de memoria)