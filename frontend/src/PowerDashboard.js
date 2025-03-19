import React, { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, Label, ReferenceLine } from 'recharts';

// API 기본 URL 설정 (환경변수 사용)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

// 색상 설정
const COLORS = {
  wind: '#8884d8',
  piezo: '#82ca9d',
  total: '#4287f5',
  consumption: '#ff8042',
  surplus: '#41ed7e',
  deficit: '#ff4d4d',
  blue: ['#8884d8', '#7366bd', '#5e48a2', '#493a87', '#342c6c'],
  green: ['#82ca9d', '#6eb589', '#5a9f75', '#468a61', '#32754c'],
  orange: ['#ff8042', '#e67037', '#cc5f2d', '#b35022', '#994118']
};

const PowerDashboard = () => {
  // 상태 관리
  const [activeTab, setActiveTab] = useState('realtime');
  const [selectedLocation, setSelectedLocation] = useState('5호관_60주년_사이');
  const [realtimePower, setRealtimePower] = useState(null);
  const [dailyPower, setDailyPower] = useState(null);
  const [weeklyPower, setWeeklyPower] = useState(null);
  const [monthlyPower, setMonthlyPower] = useState(null);
  const [annualPower, setAnnualPower] = useState(null);
  const [windSpeed, setWindSpeed] = useState(3.5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 위치 옵션
  const locationOptions = [
    { value: '5호관_60주년_사이', label: '5호관-60주년 사이' },
    { value: '인경호_앞', label: '인경호 앞' },
    { value: '하이데거숲', label: '하이데거숲' }
  ];

  // API 호출 함수
  const fetchData = async (endpoint) => {
    try {
      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API 호출 오류:', error);
      throw error;
    }
  };

  // 실시간 전력 데이터 조회
  const fetchRealtimePower = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchData(`${API_BASE_URL}/power/realtime/${selectedLocation}`);
      setRealtimePower(data);
    } catch (err) {
      console.error('실시간 전력 데이터 조회 오류:', err);
      setError(err.message || '실시간 전력 데이터 조회 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 일일 전력 데이터 조회
  const fetchDailyPower = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchData(`${API_BASE_URL}/power/daily/${selectedLocation}?avg_wind_speed=${windSpeed}`);
      setDailyPower(data);
    } catch (err) {
      console.error('일일 전력 데이터 조회 오류:', err);
      setError(err.message || '일일 전력 데이터 조회 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 주간 전력 데이터 조회
  const fetchWeeklyPower = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchData(`${API_BASE_URL}/power/weekly/${selectedLocation}?avg_wind_speed=${windSpeed}`);
      setWeeklyPower(data);
    } catch (err) {
      console.error('주간 전력 데이터 조회 오류:', err);
      setError(err.message || '주간 전력 데이터 조회 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 월간 전력 데이터 조회
  const fetchMonthlyPower = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchData(`${API_BASE_URL}/power/monthly/${selectedLocation}?avg_wind_speed=${windSpeed}&min_temp=5&max_temp=25`);
      setMonthlyPower(data);
    } catch (err) {
      console.error('월간 전력 데이터 조회 오류:', err);
      setError(err.message || '월간 전력 데이터 조회 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 연간 전력 데이터 조회
  const fetchAnnualPower = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchData(`${API_BASE_URL}/power/annual/${selectedLocation}`);
      setAnnualPower(data);
    } catch (err) {
      console.error('연간 전력 데이터 조회 오류:', err);
      setError(err.message || '연간 전력 데이터 조회 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 데이터 새로고침
  const refreshData = () => {
    if (activeTab === 'realtime') {
      fetchRealtimePower();
    } else if (activeTab === 'daily') {
      fetchDailyPower();
    } else if (activeTab === 'weekly') {
      fetchWeeklyPower();
    } else if (activeTab === 'monthly') {
      fetchMonthlyPower();
    } else if (activeTab === 'annual') {
      fetchAnnualPower();
    }
  };

  // 위치나 탭 변경 시 데이터 새로고침
  useEffect(() => {
    refreshData();
  }, [selectedLocation, activeTab]);

  // 시간 포맷 변환
  const formatHour = (hour) => {
    return `${hour}:00`;
  };

  // 단위 포맷 변환 (Wh → kWh, 필요한 경우)
  const formatEnergy = (energy, unit = 'Wh') => {
    if (unit === 'Wh' && energy >= 1000) {
      return `${(energy / 1000).toFixed(2)} kWh`;
    }
    return `${energy.toFixed(2)} ${unit}`;
  };

  // 전력 충족률 색상 결정
  const getSufficiencyColor = (percentage) => {
    if (percentage >= 150) return '#4CAF50'; // 매우 높음 (초록)
    if (percentage >= 100) return '#8BC34A'; // 충분 (연두)
    if (percentage >= 75) return '#FFC107';  // 약간 부족 (노랑)
    if (percentage >= 50) return '#FF9800';  // 부족 (주황)
    return '#F44336';  // 매우 부족 (빨강)
  };

  // 탭 메뉴 렌더링
  const renderTabs = () => (
    <div className="mb-6 border-b border-gray-200">
      <ul className="flex flex-wrap -mb-px text-sm font-medium text-center">
        <li className="mr-2">
          <button
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'realtime' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => setActiveTab('realtime')}
          >
            실시간 발전량
          </button>
        </li>
        <li className="mr-2">
          <button
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'daily' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => setActiveTab('daily')}
          >
            일일 발전량
          </button>
        </li>
        <li className="mr-2">
          <button
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'weekly' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => setActiveTab('weekly')}
          >
            주간 발전량
          </button>
        </li>
        <li className="mr-2">
          <button
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'monthly' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => setActiveTab('monthly')}
          >
            월간 발전량
          </button>
        </li>
        <li className="mr-2">
          <button
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'annual' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => setActiveTab('annual')}
          >
            연간 발전량
          </button>
        </li>
      </ul>
    </div>
  );

  // 위치 선택 및 설정 렌더링
  const renderControls = () => (
    <div className="mb-6 flex flex-wrap gap-4 items-center">
      <div className="min-w-64">
        <label className="block text-sm font-medium text-gray-700 mb-1">위치 선택</label>
        <select
          value={selectedLocation}
          onChange={(e) => setSelectedLocation(e.target.value)}
          className="w-full p-2 border rounded"
        >
          {locationOptions.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </div>

      {activeTab !== 'realtime' && activeTab !== 'annual' && (
        <div className="min-w-64">
          <label className="block text-sm font-medium text-gray-700 mb-1">평균 풍속 (m/s)</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0.5"
              max="10"
              step="0.1"
              value={windSpeed}
              onChange={(e) => setWindSpeed(parseFloat(e.target.value))}
              className="w-40"
            />
            <span className="text-sm font-semibold">{windSpeed} m/s</span>
          </div>
        </div>
      )}

      <div className="ml-auto">
        <button
          onClick={refreshData}
          disabled={loading}
          className={`px-4 py-2 rounded ${loading ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
        >
          {loading ? '로딩 중...' : '새로고침'}
        </button>
      </div>
    </div>
  );

  // 실시간 발전량 대시보드 렌더링
  const renderRealtimeDashboard = () => {
    if (!realtimePower) {
      return (
        <div className="text-center py-8 text-gray-500">
          <p>실시간 발전량 데이터를 불러오는 중입니다. '새로고침' 버튼을 눌러주세요.</p>
        </div>
      );
    }

    // 파이 차트 데이터
    const powerSourceData = [
      { name: '풍력', value: realtimePower.wind_power_wh },
      { name: '지압', value: realtimePower.piezo_power_wh }
    ];

    // 발전량과 소비량 비교 데이터
    const powerBalanceData = [
      { name: '발전량', value: realtimePower.total_power_wh },
      { name: '소비량', value: realtimePower.streetlight_consumption_wh }
    ];

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded shadow">
          <h2 className="text-xl font-semibold mb-4">실시간 발전량 요약</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">풍력 발전량</h3>
              <p className="text-2xl font-bold text-blue-700">{formatEnergy(realtimePower.wind_power_wh)}</p>
            </div>
            
            <div className="bg-green-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">지압 발전량</h3>
              <p className="text-2xl font-bold text-green-700">{formatEnergy(realtimePower.piezo_power_wh)}</p>
            </div>
            
            <div className="bg-purple-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">총 발전량</h3>
              <p className="text-2xl font-bold text-purple-700">{formatEnergy(realtimePower.total_power_wh)}</p>
            </div>
            
            <div className={`p-4 rounded ${realtimePower.is_sufficient ? 'bg-green-50' : 'bg-red-50'}`}>
              <h3 className="text-sm font-medium text-gray-600">충족률</h3>
              <p className={`text-2xl font-bold ${realtimePower.is_sufficient ? 'text-green-700' : 'text-red-700'}`}>
                {realtimePower.sufficiency_percentage.toFixed(1)}%
              </p>
            </div>
          </div>
          
          {realtimePower.weather && (
            <div className="mt-4 p-4 bg-gray-50 rounded">
              <h3 className="text-sm font-medium text-gray-600 mb-2">현재 날씨 조건</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-gray-500">풍속</p>
                  <p className="font-semibold">{realtimePower.weather.windSpeed} m/s</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">기온</p>
                  <p className="font-semibold">{realtimePower.weather.temperature}°C</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">습도</p>
                  <p className="font-semibold">{realtimePower.weather.humidity}%</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">인원 수</p>
                  <p className="font-semibold">{realtimePower.people_count} 명</p>
                </div>
              </div>
            </div>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">발전 에너지 구성</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={powerSourceData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {powerSourceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? COLORS.wind : COLORS.piezo} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value.toFixed(2)} Wh`, '발전량']} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">발전량 vs 소비량</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={powerBalanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis>
                    <Label value="전력량 (Wh)" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />
                  </YAxis>
                  <Tooltip formatter={(value) => [`${value.toFixed(2)} Wh`, '전력량']} />
                  <Legend />
                  <Bar dataKey="value" name="전력량 (Wh)">
                    {powerBalanceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? COLORS.total : COLORS.consumption} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 text-center">
              <p className={`text-lg font-semibold ${realtimePower.is_sufficient ? 'text-green-600' : 'text-red-600'}`}>
                {realtimePower.is_sufficient ? '충분한 발전량' : '부족한 발전량'}
                : {realtimePower.power_balance_wh.toFixed(2)} Wh {realtimePower.power_balance_wh >= 0 ? '여유' : '부족'}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 일일 발전량 대시보드 렌더링
  const renderDailyDashboard = () => {
    if (!dailyPower) {
      return (
        <div className="text-center py-8 text-gray-500">
          <p>일일 발전량 데이터를 불러오는 중입니다. '새로고침' 버튼을 눌러주세요.</p>
        </div>
      );
    }

    // 시간별 데이터 변환
    const hourlyData = dailyPower.hourly_results.map(hour => ({
      hour: hour.hour,
      label: formatHour(hour.hour),
      wind: hour.wind_power_wh,
      piezo: hour.piezo_power_wh,
      total: hour.total_power_wh,
      people: hour.people_count,
      windSpeed: hour.wind_speed
    }));

    // 파이 차트 데이터
    const powerSourceData = [
      { name: '풍력', value: dailyPower.daily_wind_power_wh },
      { name: '지압', value: dailyPower.daily_piezo_power_wh }
    ];

    // 충족률 게이지 데이터
    const sufficiencyData = [
      { name: '발전량', value: dailyPower.daily_total_power_wh },
      { name: '소비량', value: dailyPower.streetlight_consumption_wh }
    ];

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded shadow">
          <h2 className="text-xl font-semibold mb-4">일일 발전량 요약</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">풍력 발전량</h3>
              <p className="text-2xl font-bold text-blue-700">{formatEnergy(dailyPower.daily_wind_power_wh)}</p>
              <p className="text-xs text-gray-500">{formatEnergy(dailyPower.daily_wind_power_wh / 1000, 'kWh')}</p>
            </div>
            
            <div className="bg-green-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">지압 발전량</h3>
              <p className="text-2xl font-bold text-green-700">{formatEnergy(dailyPower.daily_piezo_power_wh)}</p>
              <p className="text-xs text-gray-500">{formatEnergy(dailyPower.daily_piezo_power_wh / 1000, 'kWh')}</p>
            </div>
            
            <div className="bg-purple-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">총 발전량</h3>
              <p className="text-2xl font-bold text-purple-700">{formatEnergy(dailyPower.daily_total_power_wh)}</p>
              <p className="text-xs text-gray-500">{formatEnergy(dailyPower.daily_total_power_wh / 1000, 'kWh')}</p>
            </div>
            
            <div className={`p-4 rounded ${dailyPower.is_sufficient ? 'bg-green-50' : 'bg-red-50'}`}>
              <h3 className="text-sm font-medium text-gray-600">충족률</h3>
              <p className={`text-2xl font-bold ${dailyPower.is_sufficient ? 'text-green-700' : 'text-red-700'}`}>
                {dailyPower.sufficiency_percentage.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500">
                {dailyPower.is_sufficient ? '전력 여유' : '전력 부족'}: {Math.abs(dailyPower.power_balance_wh).toFixed(0)} Wh
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded shadow">
          <h3 className="text-lg font-semibold mb-4">시간별 발전량</h3>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="label"
                  tick={{ fontSize: 12 }}
                  interval={3}
                  label={{ value: '시간', position: 'insideBottom', offset: -5 }}
                />
                <YAxis 
                  label={{ value: '발전량 (Wh)', angle: -90, position: 'insideLeft' }}
                  domain={[0, 'auto']}
                />
                <Tooltip 
                  formatter={(value, name) => {
                    if (name === 'wind') return [`${value.toFixed(2)} Wh`, '풍력'];
                    if (name === 'piezo') return [`${value.toFixed(2)} Wh`, '지압'];
                    if (name === 'total') return [`${value.toFixed(2)} Wh`, '총 발전량'];
                    return [value, name];
                  }}
                  labelFormatter={(label) => `${label} 시간대`}
                />
                <Legend />
                <Area 
                  type="monotone" 
                  dataKey="wind" 
                  name="풍력" 
                  stackId="1"
                  stroke={COLORS.wind} 
                  fill={COLORS.wind} 
                  fillOpacity={0.6}
                />
                <Area 
                  type="monotone" 
                  dataKey="piezo" 
                  name="지압" 
                  stackId="1"
                  stroke={COLORS.piezo} 
                  fill={COLORS.piezo} 
                  fillOpacity={0.6}
                />
                <ReferenceLine 
                  y={dailyPower.streetlight_consumption_wh / 24} 
                  label="시간당 소비량" 
                  stroke="red" 
                  strokeDasharray="3 3"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">발전 에너지 구성</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={powerSourceData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {powerSourceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? COLORS.wind : COLORS.piezo} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value.toFixed(2)} Wh`, '발전량']} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">인구 흐름 및 풍속 변화</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={hourlyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="label"
                    tick={{ fontSize: 12 }}
                    interval={3}
                  />
                  <YAxis 
                    yAxisId="left"
                    label={{ value: '인원 수 (명)', angle: -90, position: 'insideLeft' }}
                  />
                  <YAxis 
                    yAxisId="right"
                    orientation="right"
                    label={{ value: '풍속 (m/s)', angle: 90, position: 'insideRight' }}
                    domain={[0, 'auto']}
                  />
                  <Tooltip 
                    formatter={(value, name) => {
                      if (name === 'people') return [`${value} 명`, '인원 수'];
                      if (name === 'windSpeed') return [`${value} m/s`, '풍속'];
                      return [value, name];
                    }}
                    labelFormatter={(label) => `${label} 시간대`}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="people" 
                    name="인원 수" 
                    yAxisId="left"
                    stroke="#ff7300" 
                    activeDot={{ r: 8 }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="windSpeed" 
                    name="풍속" 
                    yAxisId="right"
                    stroke="#4287f5" 
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 주간 발전량 대시보드 렌더링
  const renderWeeklyDashboard = () => {
    if (!weeklyPower) {
      return (
        <div className="text-center py-8 text-gray-500">
          <p>주간 발전량 데이터를 불러오는 중입니다. '새로고침' 버튼을 눌러주세요.</p>
        </div>
      );
    }

    // 일별 발전량 데이터
    const dailyData = weeklyPower.daily_results.map(day => ({
      date: day.date,
      wind: day.daily_wind_power_wh,
      piezo: day.daily_piezo_power_wh,
      total: day.daily_total_power_wh,
      consumption: day.streetlight_consumption_wh,
      balance: day.power_balance_wh,
      sufficiency: day.sufficiency_percentage
    }));

    // 파이 차트 데이터
    const powerSourceData = [
      { name: '풍력', value: weeklyPower.weekly_wind_power_wh },
      { name: '지압', value: weeklyPower.weekly_piezo_power_wh }
    ];

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded shadow">
          <h2 className="text-xl font-semibold mb-4">주간 발전량 요약</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">풍력 발전량</h3>
              <p className="text-2xl font-bold text-blue-700">{formatEnergy(weeklyPower.weekly_wind_power_wh)}</p>
              <p className="text-sm text-gray-500">{formatEnergy(weeklyPower.weekly_wind_power_kwh, 'kWh')}</p>
            </div>
            
            <div className="bg-green-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">지압 발전량</h3>
              <p className="text-2xl font-bold text-green-700">{formatEnergy(weeklyPower.weekly_piezo_power_wh)}</p>
              <p className="text-sm text-gray-500">{formatEnergy(weeklyPower.weekly_piezo_power_kwh, 'kWh')}</p>
            </div>
            
            <div className="bg-purple-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">총 발전량</h3>
              <p className="text-2xl font-bold text-purple-700">{formatEnergy(weeklyPower.weekly_total_power_wh)}</p>
              <p className="text-sm text-gray-500">{formatEnergy(weeklyPower.weekly_total_power_kwh, 'kWh')}</p>
            </div>
            
            <div className={`p-4 rounded ${weeklyPower.is_sufficient ? 'bg-green-50' : 'bg-red-50'}`}>
              <h3 className="text-sm font-medium text-gray-600">충족률</h3>
              <p className={`text-2xl font-bold ${weeklyPower.is_sufficient ? 'text-green-700' : 'text-red-700'}`}>
                {weeklyPower.sufficiency_percentage.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-500">
                {weeklyPower.is_sufficient ? '전력 여유' : '전력 부족'}: {Math.abs(weeklyPower.power_balance_kwh).toFixed(3)} kWh
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded shadow">
          <h3 className="text-lg font-semibold mb-4">일별 발전량</h3>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  interval={0}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                  label={{ value: '날짜', position: 'insideBottom', offset: -10 }}
                />
                <YAxis 
                  label={{ value: '발전량 (Wh)', angle: -90, position: 'insideLeft' }}
                  domain={[0, 'auto']}
                />
                <Tooltip 
                  formatter={(value, name) => {
                    if (name === 'wind') return [`${value.toFixed(2)} Wh`, '풍력'];
                    if (name === 'piezo') return [`${value.toFixed(2)} Wh`, '지압'];
                    if (name === 'consumption') return [`${value.toFixed(2)} Wh`, '소비량'];
                    return [value, name];
                  }}
                  labelFormatter={(label) => `${label}`}
                />
                <Legend />
                <Bar dataKey="wind" name="풍력" stackId="a" fill={COLORS.wind} />
                <Bar dataKey="piezo" name="지압" stackId="a" fill={COLORS.piezo} />
                <ReferenceLine y={weeklyPower.streetlight_consumption_wh / 7} label="일일 소비량" stroke="red" strokeDasharray="3 3" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">발전 에너지 구성</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={powerSourceData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {powerSourceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? COLORS.wind : COLORS.piezo} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${(value / 1000).toFixed(2)} kWh`, '발전량']} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">일별 충족률</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dailyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    interval={0}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis 
                    label={{ value: '충족률 (%)', angle: -90, position: 'insideLeft' }}
                    domain={[0, 'auto']}
                  />
                  <Tooltip 
                    formatter={(value, name) => {
                      if (name === 'sufficiency') return [`${value.toFixed(1)}%`, '충족률'];
                      return [value, name];
                    }}
                  />
                  <Legend />
                  <ReferenceLine y={100} label="100% (완전 충족)" stroke="green" strokeDasharray="3 3" />
                  <Line 
                    type="monotone" 
                    dataKey="sufficiency" 
                    name="충족률" 
                    stroke="#ff7300" 
                    activeDot={{ r: 8 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 월간 발전량 대시보드 렌더링
  const renderMonthlyDashboard = () => {
    if (!monthlyPower) {
      return (
        <div className="text-center py-8 text-gray-500">
          <p>월간 발전량 데이터를 불러오는 중입니다. '새로고침' 버튼을 눌러주세요.</p>
        </div>
      );
    }

    // 주별 발전량 데이터
    const weeklyData = monthlyPower.weekly_results.map((week, index) => ({
      week: `Week ${index + 1}`,
      wind: week.weekly_wind_power_wh,
      piezo: week.weekly_piezo_power_wh,
      total: week.weekly_total_power_wh,
      consumption: week.streetlight_consumption_wh,
      balance: week.power_balance_wh,
      sufficiency: week.sufficiency_percentage
    }));

    // 파이 차트 데이터
    const powerSourceData = [
      { name: '풍력', value: monthlyPower.monthly_wind_power_wh },
      { name: '지압', value: monthlyPower.monthly_piezo_power_wh }
    ];

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded shadow">
          <h2 className="text-xl font-semibold mb-4">월간 발전량 요약</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">풍력 발전량</h3>
              <p className="text-xl font-bold text-blue-700">{formatEnergy(monthlyPower.monthly_wind_power_kwh, 'kWh')}</p>
              <p className="text-xs text-gray-500">{formatEnergy(monthlyPower.monthly_wind_power_wh)} / 30일</p>
            </div>
            
            <div className="bg-green-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">지압 발전량</h3>
              <p className="text-xl font-bold text-green-700">{formatEnergy(monthlyPower.monthly_piezo_power_kwh, 'kWh')}</p>
              <p className="text-xs text-gray-500">{formatEnergy(monthlyPower.monthly_piezo_power_wh)} / 30일</p>
            </div>
            
            <div className="bg-purple-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">총 발전량</h3>
              <p className="text-xl font-bold text-purple-700">{formatEnergy(monthlyPower.monthly_total_power_kwh, 'kWh')}</p>
              <p className="text-xs text-gray-500">{formatEnergy(monthlyPower.monthly_total_power_wh)} / 30일</p>
            </div>
            
            <div className={`p-4 rounded ${monthlyPower.is_sufficient ? 'bg-green-50' : 'bg-red-50'}`}>
              <h3 className="text-sm font-medium text-gray-600">충족률</h3>
              <p className={`text-xl font-bold ${monthlyPower.is_sufficient ? 'text-green-700' : 'text-red-700'}`}>
                {monthlyPower.sufficiency_percentage.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500">
                {monthlyPower.is_sufficient ? '전력 여유' : '전력 부족'}: {Math.abs(monthlyPower.power_balance_kwh).toFixed(2)} kWh
              </p>
            </div>
          </div>
          
          <div className="mt-4 p-4 bg-gray-50 rounded">
            <h3 className="text-sm font-medium text-gray-600 mb-2">환경 조건</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500">평균 풍속</p>
                <p className="font-semibold">{monthlyPower.avg_wind_speed} m/s</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">가로등 개수</p>
                <p className="font-semibold">{weeklyPower ? weeklyPower.daily_results[0].streetlight_consumption_wh / 150 / 12 : '-'} 개</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">소비 전력</p>
                <p className="font-semibold">{formatEnergy(monthlyPower.streetlight_consumption_kwh, 'kWh')}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">일평균 발전량</p>
                <p className="font-semibold">{formatEnergy(monthlyPower.monthly_total_power_wh / 30)}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded shadow">
          <h3 className="text-lg font-semibold mb-4">주별 발전량</h3>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="week"
                  tick={{ fontSize: 12 }}
                />
                <YAxis 
                  label={{ value: '발전량 (kWh)', angle: -90, position: 'insideLeft' }}
                  tickFormatter={(value) => (value / 1000).toFixed(1)}
                />
                <Tooltip 
                  formatter={(value, name) => {
                    if (name === 'wind') return [`${(value / 1000).toFixed(2)} kWh`, '풍력'];
                    if (name === 'piezo') return [`${(value / 1000).toFixed(2)} kWh`, '지압'];
                    if (name === 'consumption') return [`${(value / 1000).toFixed(2)} kWh`, '소비량'];
                    return [value, name];
                  }}
                />
                <Legend />
                <Bar dataKey="wind" name="풍력" stackId="a" fill={COLORS.wind} />
                <Bar dataKey="piezo" name="지압" stackId="a" fill={COLORS.piezo} />
                <ReferenceLine y={monthlyPower.streetlight_consumption_wh / 4} label="주간 소비량" stroke="red" strokeDasharray="3 3" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">발전 에너지 구성</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={powerSourceData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {powerSourceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? COLORS.wind : COLORS.piezo} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${(value / 1000).toFixed(2)} kWh`, '발전량']} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">주별 충족률</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weeklyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="week" />
                  <YAxis 
                    label={{ value: '충족률 (%)', angle: -90, position: 'insideLeft' }}
                    domain={[0, 'auto']}
                  />
                  <Tooltip 
                    formatter={(value, name) => {
                      if (name === 'sufficiency') return [`${value.toFixed(1)}%`, '충족률'];
                      return [value, name];
                    }}
                  />
                  <Legend />
                  <ReferenceLine y={100} label="100% (완전 충족)" stroke="green" strokeDasharray="3 3" />
                  <Line 
                    type="monotone" 
                    dataKey="sufficiency" 
                    name="충족률" 
                    stroke="#ff7300" 
                    activeDot={{ r: 8 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 연간 발전량 대시보드 렌더링
  const renderAnnualDashboard = () => {
    if (!annualPower) {
      return (
        <div className="text-center py-8 text-gray-500">
          <p>연간 발전량 데이터를 불러오는 중입니다. '새로고침' 버튼을 눌러주세요.</p>
        </div>
      );
    }

    // 월별 발전량 데이터
    const monthlyData = annualPower.monthly_results.map(month => ({
      month: month.month,
      wind: month.monthly_wind_power_wh,
      piezo: month.monthly_piezo_power_wh,
      total: month.monthly_total_power_wh,
      consumption: month.streetlight_consumption_wh,
      balance: month.power_balance_wh,
      sufficiency: month.sufficiency_percentage
    }));

    // 파이 차트 데이터
    const powerSourceData = [
      { name: '풍력', value: annualPower.annual_wind_power_wh },
      { name: '지압', value: annualPower.annual_piezo_power_wh }
    ];

    // 계절별 발전량 데이터
    const seasonalData = [
      { 
        name: '봄 (3-5월)', 
        wind: (monthlyData[2].wind + monthlyData[3].wind + monthlyData[4].wind) / 3, 
        piezo: (monthlyData[2].piezo + monthlyData[3].piezo + monthlyData[4].piezo) / 3,
        sufficiency: (monthlyData[2].sufficiency + monthlyData[3].sufficiency + monthlyData[4].sufficiency) / 3
      },
      { 
        name: '여름 (6-8월)', 
        wind: (monthlyData[5].wind + monthlyData[6].wind + monthlyData[7].wind) / 3, 
        piezo: (monthlyData[5].piezo + monthlyData[6].piezo + monthlyData[7].piezo) / 3,
        sufficiency: (monthlyData[5].sufficiency + monthlyData[6].sufficiency + monthlyData[7].sufficiency) / 3
      },
      { 
        name: '가을 (9-11월)', 
        wind: (monthlyData[8].wind + monthlyData[9].wind + monthlyData[10].wind) / 3, 
        piezo: (monthlyData[8].piezo + monthlyData[9].piezo + monthlyData[10].piezo) / 3,
        sufficiency: (monthlyData[8].sufficiency + monthlyData[9].sufficiency + monthlyData[10].sufficiency) / 3
      },
      { 
        name: '겨울 (12-2월)', 
        wind: (monthlyData[11].wind + monthlyData[0].wind + monthlyData[1].wind) / 3, 
        piezo: (monthlyData[11].piezo + monthlyData[0].piezo + monthlyData[1].piezo) / 3,
        sufficiency: (monthlyData[11].sufficiency + monthlyData[0].sufficiency + monthlyData[1].sufficiency) / 3
      }
    ];

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded shadow">
          <h2 className="text-xl font-semibold mb-4">연간 발전량 요약</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">풍력 발전량</h3>
              <p className="text-xl font-bold text-blue-700">{formatEnergy(annualPower.annual_wind_power_kwh, 'kWh')}</p>
              <p className="text-xs text-gray-500">연간 총량</p>
            </div>
            
            <div className="bg-green-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">지압 발전량</h3>
              <p className="text-xl font-bold text-green-700">{formatEnergy(annualPower.annual_piezo_power_kwh, 'kWh')}</p>
              <p className="text-xs text-gray-500">연간 총량</p>
            </div>
            
            <div className="bg-purple-50 p-4 rounded">
              <h3 className="text-sm font-medium text-gray-600">총 발전량</h3>
              <p className="text-xl font-bold text-purple-700">{formatEnergy(annualPower.annual_total_power_kwh, 'kWh')}</p>
              <p className="text-xs text-gray-500">연간 총량</p>
            </div>
            
            <div className={`p-4 rounded ${annualPower.is_sufficient ? 'bg-green-50' : 'bg-red-50'}`}>
              <h3 className="text-sm font-medium text-gray-600">충족률</h3>
              <p className={`text-xl font-bold ${annualPower.is_sufficient ? 'text-green-700' : 'text-red-700'}`}>
                {annualPower.sufficiency_percentage.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500">
                {annualPower.is_sufficient ? '전력 여유' : '전력 부족'}: {Math.abs(annualPower.power_balance_kwh).toFixed(2)} kWh
              </p>
            </div>
          </div>
          
          <div className="mt-4 p-4 bg-gray-50 rounded">
            <h3 className="text-sm font-medium text-gray-600 mb-2">연간 요약</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500">가로등 개수</p>
                <p className="font-semibold">{annualPower.streetlight_consumption_wh / (150 * 12 * 365)} 개</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">소비 전력</p>
                <p className="font-semibold">{formatEnergy(annualPower.streetlight_consumption_kwh, 'kWh')}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">월평균 발전량</p>
                <p className="font-semibold">{formatEnergy(annualPower.annual_total_power_wh / 12 / 1000, 'kWh')}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">일평균 발전량</p>
                <p className="font-semibold">{formatEnergy(annualPower.annual_total_power_wh / 365, 'Wh')}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded shadow">
          <h3 className="text-lg font-semibold mb-4">월별 발전량</h3>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="month"
                  tick={{ fontSize: 12 }}
                />
                <YAxis 
                  label={{ value: '발전량 (kWh)', angle: -90, position: 'insideLeft' }}
                  tickFormatter={(value) => (value / 1000).toFixed(1)}
                />
                <Tooltip 
                  formatter={(value, name) => {
                    if (name === 'wind') return [`${(value / 1000).toFixed(2)} kWh`, '풍력'];
                    if (name === 'piezo') return [`${(value / 1000).toFixed(2)} kWh`, '지압'];
                    return [value, name];
                  }}
                />
                <Legend />
                <Bar dataKey="wind" name="풍력" stackId="a" fill={COLORS.wind} />
                <Bar dataKey="piezo" name="지압" stackId="a" fill={COLORS.piezo} />
                <ReferenceLine y={annualPower.streetlight_consumption_wh / 12} label="월간 소비량" stroke="red" strokeDasharray="3 3" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">발전 에너지 구성</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={powerSourceData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {powerSourceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? COLORS.wind : COLORS.piezo} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${(value / 1000).toFixed(2)} kWh`, '발전량']} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="bg-white p-6 rounded shadow">
            <h3 className="text-lg font-semibold mb-4">계절별 발전량</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={seasonalData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis 
                    yAxisId="left"
                    label={{ value: '발전량 (kWh)', angle: -90, position: 'insideLeft' }}
                    tickFormatter={(value) => (value / 1000).toFixed(1)}
                  />
                  <YAxis 
                    yAxisId="right"
                    orientation="right"
                    label={{ value: '충족률 (%)', angle: 90, position: 'insideRight' }}
                    domain={[0, 'auto']}
                  />
                  <Tooltip 
                    formatter={(value, name) => {
                      if (name === 'wind') return [`${(value / 1000).toFixed(2)} kWh`, '풍력'];
                      if (name === 'piezo') return [`${(value / 1000).toFixed(2)} kWh`, '지압'];
                      if (name === 'sufficiency') return [`${value.toFixed(1)}%`, '충족률'];
                      return [value, name];
                    }}
                  />
                  <Legend />
                  <Bar yAxisId="left" dataKey="wind" name="풍력" stackId="a" fill={COLORS.wind} />
                  <Bar yAxisId="left" dataKey="piezo" name="지압" stackId="a" fill={COLORS.piezo} />
                  <Line 
                    yAxisId="right"
                    type="monotone" 
                    dataKey="sufficiency" 
                    name="충족률" 
                    stroke="#ff7300" 
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded shadow">
          <h3 className="text-lg font-semibold mb-4">월별 충족률</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis 
                  label={{ value: '충족률 (%)', angle: -90, position: 'insideLeft' }}
                  domain={[0, 'auto']}
                />
                <Tooltip 
                  formatter={(value, name) => {
                    if (name === 'sufficiency') return [`${value.toFixed(1)}%`, '충족률'];
                    return [value, name];
                  }}
                />
                <Legend />
                <ReferenceLine y={100} label="100% (완전 충족)" stroke="green" strokeDasharray="3 3" />
                <Line 
                  type="monotone" 
                  dataKey="sufficiency" 
                  name="충족률" 
                  stroke="#ff7300" 
                  activeDot={{ r: 8 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    );
  };

  // 메인 대시보드 렌더링
  return (
    <div className="flex flex-col p-6 max-w-6xl mx-auto bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-2 text-center text-gray-800">전력 발전량 대시보드</h1>
      <p className="text-center text-gray-600 mb-6">풍력 및 지압 발전 시스템 통합 모니터링</p>
      
      {renderTabs()}
      {renderControls()}
      
      {error && (
        <div className="mb-6 p-4 bg-red-100 text-red-700 rounded">
          <p className="font-semibold">오류 발생:</p>
          <p>{error}</p>
        </div>
      )}
      
      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-blue-600">데이터 로딩 중...</p>
        </div>
      ) : (
        <>
          {activeTab === 'realtime' && renderRealtimeDashboard()}
          {activeTab === 'daily' && renderDailyDashboard()}
          {activeTab === 'weekly' && renderWeeklyDashboard()}
          {activeTab === 'monthly' && renderMonthlyDashboard()}
          {activeTab === 'annual' && renderAnnualDashboard()}
        </>
      )}
      
      <div className="mt-8 text-center text-gray-500 text-sm">
        <p>전력 발전량 대시보드 v1.0.0 &copy; {new Date().getFullYear()}</p>
      </div>
    </div>
  );
};

export default PowerDashboard;