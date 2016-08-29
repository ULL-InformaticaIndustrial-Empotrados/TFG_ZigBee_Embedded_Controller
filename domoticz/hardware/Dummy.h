#pragma once

#include "DomoticzHardware.h"
#include <iostream>

class CDummy : public CDomoticzHardwareBase
{
public:
	explicit CDummy(const int ID);
	~CDummy(void);
	bool WriteToHardware(const char *pdata, const unsigned char length);
	static bool CreateVirtualSensor(int idx,
			std::string ssensorname,
			std::string ssensortype,
			std::string soptions
		);
private:
	void Init();
	bool StartHardware();
	bool StopHardware();
};

