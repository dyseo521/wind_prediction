import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, Cell, PieChart, Pie
} from 'recharts';
import axios from 'axios';

// API 기본 URL 설정 (환경변수 사용)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

const WindSpeedPredictor = () => {
  // 상태 관리
  const [inputs, setInputs] = useState({
    avgHumidity: 60,
    minHumidity: 50,
    avgTemp: 20,
    maxTemp: 25,
    minTemp: 15,
    rainfall: 0,
    maxHourlyRainfall: 0
  });
  const [prediction, setPrediction] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('predict');
  const [files, setFiles] = useState({
    wind: null,
    humidity: null,
    temp: null,
    rain: null
  });
  const [uploadStatus, setUploadStatus] = useState({
    wind: null,
    humidity: null,
    temp: null,
    rain: null
  });
  const [trainingParams, setTrainingParams] = useState({
    testSize: 0.2,
    alpha: 0.1,
    polynomialDegree: 2
  });
  const [trainStatus, setTrainStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [forecastInputs, setForecastInputs] = useState({
    date: new Date().toISOString().split('T')[0],
    location: '인천광역시 미추홀구 용현1.4동',
    avgHumidity: 60,
    avgTemp: 20,
    rainfallProb: 0
  });
  const [currentWeather, setCurrentWeather] = useState(null);
  const [weatherForecast, setWeatherForecast] = useState(null);
  const [loadingWeather, setLoadingWeather] = useState(false);
  const [apiKeyTestResult, setApiKeyTestResult] = useState(null);

  // 사용자 입력값 변경 처리
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setInputs(prev => ({ ...prev, [name]: parseFloat(value) }));
  };

  // 예측 요청 함수
  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const endpoint = selectedModel 
        ? `${API_BASE_URL}/predict/${selectedModel}` 
        : `${API_BASE_URL}/predict/`;
      
      const response = await axios.post(endpoint, inputs);
      setPrediction(response.data);
      
      // 온도 변화에 따른 차트 데이터 생성
      generateChartData();
    } catch (err) {
      console.error('예측 오류:', err);
      setError(err.response?.data?.detail || '예측 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 현재 날씨 데이터로 예측 수행
  const handlePredictWithCurrentWeather = async () => {
    if (!currentWeather) {
      setError('먼저 현재 날씨 데이터를 가져와야 합니다.');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      // 현재 날씨 데이터로 입력값 설정
      const weatherData = currentWeather.weather;
      const weatherInputs = {
        avgHumidity: weatherData.humidity || 60,
        minHumidity: Math.max(20, (weatherData.humidity || 60) - 10),
        avgTemp: weatherData.temperature || 20,
        maxTemp: (weatherData.temperature || 20) + 5,
        minTemp: (weatherData.temperature || 20) - 5,
        rainfall: weatherData.rainfall || 0,
        maxHourlyRainfall: (weatherData.rainfall || 0) / 2
      };

      // 예측 요청
      const endpoint = selectedModel 
        ? `${API_BASE_URL}/predict/${selectedModel}` 
        : `${API_BASE_URL}/predict/`;
      
      const response = await axios.post(endpoint, weatherInputs);
      
      // 결과에 현재 날씨 정보 추가
      const resultWithWeather = {
        ...response.data,
        currentWeather: currentWeather
      };
      
      setPrediction(resultWithWeather);
      
    } catch (err) {
      console.error('현재 날씨 기반 예측 오류:', err);
      setError(err.response?.data?.detail || '예측 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 차트 데이터 생성
  const generateChartData = async () => {
    const tempChartData = [];
    const baseTemp = inputs.avgTemp;
    
    for (let tempDiff = -10; tempDiff <= 10; tempDiff += 2) {
      const tempValue = baseTemp + tempDiff;
      
      // 기온 변화를 적용한 새로운 입력값
      const newInputs = { 
        ...inputs, 
        avgTemp: tempValue,
        maxTemp: tempValue + 5,
        minTemp: tempValue - 5
      };
      
      try {
        const response = await axios.post(`${API_BASE_URL}/predict/`, newInputs);
        
        tempChartData.push({
          temperature: tempValue,
          predictedWindSpeed: response.data.predicted_wind_speed
        });
      } catch (err) {
        console.error('차트 데이터 생성 오류:', err);
      }
    }
    
    // 온도 순으로 정렬
    tempChartData.sort((a, b) => a.temperature - b.temperature);
    setChartData(tempChartData);
  };

  // 현재 날씨 데이터 가져오기
  const fetchCurrentWeather = async () => {
    setLoadingWeather(true);
    setError(null);

    try {
      // 직접 기상청 API를 호출하지 않고 백엔드 API를 통해 호출
      const response = await axios.get(`${API_BASE_URL}/weather/current`);
      
      // 응답 데이터 확인 및 로깅
      console.log('Current weather API response:', response.data);
      
      if (!response.data) {
        throw new Error('날씨 데이터가 비어 있습니다.');
      }
      
      setCurrentWeather(response.data);

      // 현재 날씨 데이터로 입력값 업데이트
      if (response.data.weather) {
        const weatherData = response.data.weather;
        setInputs(prev => ({
          ...prev,
          avgHumidity: weatherData.humidity || prev.avgHumidity,
          minHumidity: Math.max(20, (weatherData.humidity || prev.avgHumidity) - 10),
          avgTemp: weatherData.temperature || prev.avgTemp,
          maxTemp: (weatherData.temperature || prev.avgTemp) + 5,
          minTemp: (weatherData.temperature || prev.avgTemp) - 5,
          rainfall: weatherData.rainfall || prev.rainfall,
          maxHourlyRainfall: (weatherData.rainfall || prev.rainfall) / 2
        }));
      }
    } catch (err) {
      console.error('현재 날씨 데이터 조회 오류:', err);
      
      // 더 자세한 오류 메시지 제공
      let errorMessage = '현재 날씨 데이터를 가져오지 못했습니다.';
      if (err.response) {
        console.error('Error response data:', err.response.data);
        errorMessage += ` 서버 응답 코드: ${err.response.status}`;
        if (err.response.data && err.response.data.detail) {
          errorMessage += ` (${err.response.data.detail})`;
        }
      } else if (err.request) {
        errorMessage += ' 서버로부터 응답이 없습니다. 네트워크 연결을 확인하세요.';
      } else {
        errorMessage += ` ${err.message}`;
      }
      
      setError(errorMessage);
    } finally {
      setLoadingWeather(false);
    }
  };

  // 단기 예보 데이터 가져오기
  const fetchShortForecast = async () => {
    setLoadingWeather(true);
    setError(null);

    try {
      // 직접 기상청 API를 호출하지 않고 백엔드 API를 통해 호출
      const response = await axios.get(`${API_BASE_URL}/weather/forecast/short`);
      
      // 응답 데이터 확인 및 로깅
      console.log('Short forecast API response:', response.data);
      
      if (!response.data) {
        throw new Error('예보 데이터가 비어 있습니다.');
      }
      
      setWeatherForecast(response.data);

      // 첫 번째 예보 데이터로 예보 입력값 업데이트
      if (response.data.forecasts && response.data.forecasts.length > 0) {
        const firstForecast = response.data.forecasts[0].weather;
        setForecastInputs(prev => ({
          ...prev,
          avgHumidity: firstForecast.humidity || prev.avgHumidity,
          avgTemp: firstForecast.temperature || prev.avgTemp,
          rainfallProb: firstForecast.precipitationProbability || prev.rainfallProb
        }));
      }
    } catch (err) {
      console.error('단기 예보 데이터 조회 오류:', err);
      
      // 더 자세한 오류 메시지 제공
      let errorMessage = '단기 예보 데이터를 가져오지 못했습니다.';
      if (err.response) {
        console.error('Error response data:', err.response.data);
        errorMessage += ` 서버 응답 코드: ${err.response.status}`;
        if (err.response.data && err.response.data.detail) {
          errorMessage += ` (${err.response.data.detail})`;
        }
      } else if (err.request) {
        errorMessage += ' 서버로부터 응답이 없습니다. 네트워크 연결을 확인하세요.';
      } else {
        errorMessage += ` ${err.message}`;
      }
      
      setError(errorMessage);
    } finally {
      setLoadingWeather(false);
    }
  };

  // API 키 테스트 함수
  const testApiKey = async () => {
    setLoadingWeather(true);
    setError(null);
    setApiKeyTestResult(null);
    
    try {
      const response = await axios.get(`${API_BASE_URL}/weather/test-api-key`);
      console.log('API Key Test Response:', response.data);
      setApiKeyTestResult(response.data);
    } catch (err) {
      console.error('API 키 테스트 오류:', err);
      setError('API 키 테스트 중 오류가 발생했습니다.');
      setApiKeyTestResult({
        status: 'error',
        message: err.response?.data?.detail || '알 수 없는 오류'
      });
    } finally {
      setLoadingWeather(false);
    }
  };

  // 파일 선택 처리
  const handleFileChange = (e, fileType) => {
    setFiles({
      ...files,
      [fileType]: e.target.files[0]
    });
  };

  // 파일 업로드 처리
  const handleFileUpload = async (fileType) => {
    if (!files[fileType]) {
      setError(`${fileType} 파일을 선택해주세요.`);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('file', files[fileType]);
      
      const response = await axios.post(`${API_BASE_URL}/upload/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setUploadStatus({
        ...uploadStatus,
        [fileType]: response.data.file_id
      });
      
    } catch (err) {
      console.error('파일 업로드 오류:', err);
      setError(err.response?.data?.detail || '파일 업로드 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 훈련 파라미터 변경 처리
  const handleTrainingParamChange = (e) => {
    const { name, value } = e.target;
    setTrainingParams(prev => ({ 
      ...prev, 
      [name]: name === 'polynomialDegree' ? parseInt(value) : parseFloat(value) 
    }));
  };

  // 모델 훈련 요청
  const handleTrainModel = async () => {
    // 모든 파일이 업로드되었는지 확인
    const allFilesUploaded = Object.values(uploadStatus).every(status => status !== null);
    
    if (!allFilesUploaded) {
      setError('모든 필요한 파일을 먼저 업로드해주세요.');
      return;
    }
    
    setLoading(true);
    setError(null);
    setTrainStatus({
      status: 'training',
      message: '모델 훈련 중...'
    });
    
    try {
      const response = await axios.post(`${API_BASE_URL}/train/`, {
        wind_file_id: uploadStatus.wind,
        humidity_file_id: uploadStatus.humidity,
        temp_file_id: uploadStatus.temp,
        rain_file_id: uploadStatus.rain,
        test_size: trainingParams.testSize,
        alpha: trainingParams.alpha,
        polynomial_degree: trainingParams.polynomialDegree
      });
      
      // 훈련 상태 확인을 위한 모델 ID 저장
      setTrainStatus({
        status: 'started',
        model_id: response.data.model_id,
        message: '모델 훈련이 시작되었습니다. 잠시 후 상태를 확인하세요.'
      });
      
      // 훈련 상태 폴링 시작
      pollTrainingStatus(response.data.model_id);
      
    } catch (err) {
      console.error('모델 훈련 오류:', err);
      setError(err.response?.data?.detail || '모델 훈련 중 오류가 발생했습니다.');
      setTrainStatus({
        status: 'failed',
        message: '모델 훈련에 실패했습니다.'
      });
    } finally {
      setLoading(false);
    }
  };

  // 훈련 상태 폴링 함수
  const pollTrainingStatus = async (modelId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/training_status/${modelId}`);
      
      if (response.data.status === 'completed') {
        setTrainStatus({
          status: 'completed',
          model_id: modelId,
          result: response.data,
          message: '모델 훈련이 완료되었습니다.'
        });
        
        // 모델 목록 갱신
        fetchModels();
        return;
      } else if (response.data.status === 'failed') {
        setTrainStatus({
          status: 'failed',
          message: `모델 훈련에 실패했습니다: ${response.data.error || '알 수 없는 오류'}`
        });
        return;
      }
      
      // 아직 훈련 중이면 3초 후 다시 확인
      setTimeout(() => pollTrainingStatus(modelId), 3000);
      
    } catch (err) {
      console.error('훈련 상태 확인 오류:', err);
      setError('훈련 상태 확인 중 오류가 발생했습니다.');
      
      // 오류가 발생해도 3초 후 다시 시도
      setTimeout(() => pollTrainingStatus(modelId), 3000);
    }
  };

  // 모델 목록 조회
  const fetchModels = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/models/`);
      setModels(response.data.models);
    } catch (err) {
      console.error('모델 목록 조회 오류:', err);
      setError('모델 목록을 가져오는 중 오류가 발생했습니다.');
    }
  };

  // 모델 선택 처리
  const handleModelSelect = (modelId) => {
    setSelectedModel(modelId);
  };

  // 날씨 예보 입력 변경 처리
  const handleForecastInputChange = (e) => {
    const { name, value } = e.target;
    setForecastInputs(prev => ({ 
      ...prev, 
      [name]: name === 'date' || name === 'location' ? value : parseFloat(value) 
    }));
  };

  // 예보 기반 풍속 예측
  const handleForecast = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('date', forecastInputs.date);
      formData.append('location', forecastInputs.location);
      formData.append('avg_humidity', forecastInputs.avgHumidity);
      formData.append('avg_temp', forecastInputs.avgTemp);
      formData.append('rainfall_prob', forecastInputs.rainfallProb);
      
      const response = await axios.post(`${API_BASE_URL}/forecast/`, formData);
      setPrediction(response.data);
      
    } catch (err) {
      console.error('예보 오류:', err);
      setError(err.response?.data?.detail || '예보 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 초기 데이터 로드
  useEffect(() => {
    fetchModels();
  }, []);

  // 강수형태 코드 변환
  const getPrecipitationType = (code) => {
    const codeMap = {
      '0': '없음',
      '1': '비',
      '2': '비/눈',
      '3': '눈',
      '4': '소나기',
      '5': '빗방울',
      '6': '빗방울눈날림',
      '7': '눈날림'
    };
    return codeMap[code] || '알 수 없음';
  };

  // 하늘상태 코드 변환
  const getSkyCondition = (code) => {
    const codeMap = {
      '1': '맑음',
      '3': '구름많음',
      '4': '흐림'
    };
    return codeMap[code] || '알 수 없음';
  };

  // 풍속 단계 판정 함수
  const getWindLevel = (speed) => {
    if (speed < 0.3) return { level: '고요', description: '바람이 거의 없음' };
    if (speed < 1.6) return { level: '미풍', description: '가벼운 바람' };
    if (speed < 3.4) return { level: '약풍', description: '잎이 살랑거림' };
    if (speed < 5.5) return { level: '남풍', description: '나뭇잎과 작은 가지가 흔들림' };
    if (speed < 8.0) return { level: '창풍', description: '작은 나무가 흔들림' };
    if (speed < 10.8) return { level: '질풍', description: '큰 나뭇가지가 흔들림' };
    if (speed < 13.9) return { level: '강풍', description: '나무 전체가 흔들림' };
    if (speed < 17.2) return { level: '폭풍', description: '나뭇가지가 부러짐' };
    return { level: '폭풍 이상', description: '구조물 손상 가능성' };
  };

  // 날짜 포맷팅 함수
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    
    // YYYYMMDD 형식을 YYYY-MM-DD로 변환
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const day = dateStr.substring(6, 8);
    
    return `${year}-${month}-${day}`;
  };

  // 시간 포맷팅 함수
  const formatTime = (timeStr) => {
    if (!timeStr) return '';
    
    // HHMM 형식을 HH:MM로 변환
    const hour = timeStr.substring(0, 2);
    const minute = timeStr.substring(2, 4);
    
    return `${hour}:${minute}`;
  };

  // 탭 메뉴
  const renderTabs = () => (
    <div className="mb-6 border-b border-gray-200">
      <ul className="flex flex-wrap -mb-px">
        <li className="mr-2">
          <button 
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'predict' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => setActiveTab('predict')}
          >
            풍속 예측
          </button>
        </li>
        <li className="mr-2">
          <button 
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'realtime' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => {
              setActiveTab('realtime');
              fetchCurrentWeather();
            }}
          >
            실시간 예측
          </button>
        </li>
        <li className="mr-2">
          <button 
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'train' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => setActiveTab('train')}
          >
            모델 훈련
          </button>
        </li>
        <li className="mr-2">
          <button 
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'models' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => setActiveTab('models')}
          >
            모델 관리
          </button>
        </li>
        <li className="mr-2">
          <button 
            className={`inline-block p-4 rounded-t-lg ${activeTab === 'forecast' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-600'}`}
            onClick={() => {
              setActiveTab('forecast');
              fetchShortForecast();
            }}
          >
            날씨 예보
          </button>
        </li>
      </ul>
    </div>
  );

  // 예측 탭 렌더링
  const renderPredictTab = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* 입력 폼 */}
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-semibold mb-4">기상 데이터 입력</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">평균습도 (%rh)</label>
            <input
              type="range"
              name="avgHumidity"
              min="0"
              max="100"
              value={inputs.avgHumidity}
              onChange={handleInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>0</span>
              <span>{inputs.avgHumidity}</span>
              <span>100</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">최저습도 (%rh)</label>
            <input
              type="range"
              name="minHumidity"
              min="0"
              max="100"
              value={inputs.minHumidity}
              onChange={handleInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>0</span>
              <span>{inputs.minHumidity}</span>
              <span>100</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">평균기온 (℃)</label>
            <input
              type="range"
              name="avgTemp"
              min="-20"
              max="40"
              value={inputs.avgTemp}
              onChange={handleInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>-20</span>
              <span>{inputs.avgTemp}</span>
              <span>40</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">최고기온 (℃)</label>
            <input
              type="range"
              name="maxTemp"
              min="-20"
              max="40"
              value={inputs.maxTemp}
              onChange={handleInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>-20</span>
              <span>{inputs.maxTemp}</span>
              <span>40</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">최저기온 (℃)</label>
            <input
              type="range"
              name="minTemp"
              min="-20"
              max="40"
              value={inputs.minTemp}
              onChange={handleInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>-20</span>
              <span>{inputs.minTemp}</span>
              <span>40</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">강수량 (mm)</label>
            <input
              type="range"
              name="rainfall"
              min="0"
              max="100"
              value={inputs.rainfall}
              onChange={handleInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>0</span>
              <span>{inputs.rainfall}</span>
              <span>100</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">1시간최다강수량 (mm)</label>
            <input
              type="range"
              name="maxHourlyRainfall"
              min="0"
              max="50"
              value={inputs.maxHourlyRainfall}
              onChange={handleInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>0</span>
              <span>{inputs.maxHourlyRainfall}</span>
              <span>50</span>
            </div>
          </div>
          
          {models.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">사용할 모델</label>
              <select 
                className="w-full p-2 border rounded"
                value={selectedModel || ""}
                onChange={(e) => handleModelSelect(e.target.value || null)}
              >
                <option value="">기본 모델</option>
                {models.map(model => (
                  <option key={model.model_id} value={model.model_id}>
                    {model.model_id} - R²: {model.metrics?.polynomial?.r2.toFixed(3) || 'N/A'}
                  </option>
                ))}
              </select>
            </div>
          )}
          
          <button
            onClick={handlePredict}
            disabled={loading}
            className={`w-full py-2 px-4 rounded transition ${loading ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
          >
            {loading ? '예측 중...' : '풍속 예측하기'}
          </button>
          
          {error && (
            <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
              {error}
            </div>
          )}
        </div>
      </div>
      
      {/* 예측 결과 */}
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-semibold mb-4">예측 결과</h2>
        
        {prediction === null ? (
          <div className="text-center py-8 text-gray-500">
            <p>왼쪽 폼에서 기상 데이터를 입력하고 예측 버튼을 눌러주세요.</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="text-center">
              <div className="text-5xl font-bold text-blue-600">
                {prediction.predicted_wind_speed.toFixed(2)} <span className="text-2xl">m/s</span>
              </div>
              <p className="mt-2 text-gray-600">예측 평균 풍속</p>
              <div className="mt-1 text-sm text-gray-500">
                신뢰도: {(prediction.confidence * 100).toFixed(0)}% | 처리 시간: {prediction.execution_time.toFixed(3)}초
              </div>
            </div>
            
            <div className="bg-gray-100 p-4 rounded">
              <h3 className="font-semibold">풍속 단계</h3>
              <div className="mt-2">
                <div className="text-xl font-bold">{prediction.wind_level}</div>
                <p className="text-gray-600">{prediction.wind_description}</p>
              </div>
            </div>
            
            {chartData.length > 0 && (
              <div>
                <h3 className="font-semibold mb-2">온도 변화에 따른 예측 풍속</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="temperature" 
                        label={{ value: '평균 기온(℃)', position: 'insideBottom', offset: -5 }} 
                      />
                      <YAxis 
                        label={{ value: '풍속(m/s)', angle: -90, position: 'insideLeft' }} 
                      />
                      <Tooltip formatter={(value) => [value.toFixed(2) + ' m/s', '예측 풍속']} />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="predictedWindSpeed" 
                        name="예측 풍속" 
                        stroke="#8884d8" 
                        activeDot={{ r: 8 }} 
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            
            {prediction.feature_importance && (
              <div>
                <h3 className="font-semibold mb-2">특성 중요도</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.entries(prediction.feature_importance)
                        .map(([feature, importance]) => ({ feature, importance: Math.abs(importance) }))
                        .sort((a, b) => b.importance - a.importance)}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis dataKey="feature" type="category" width={100} />
                      <Tooltip formatter={(value) => [value.toFixed(4), '중요도']} />
                      <Bar dataKey="importance" fill="#8884d8" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            
            <div className="text-sm text-gray-500 mt-2">
              <p>* 이 예측은 모델을 기반으로 하며, 실제 기상 조건에 따라 달라질 수 있습니다.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // 실시간 예측 탭 렌더링
  const renderRealtimeTab = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* 현재 날씨 정보 */}
      <div className="bg-white p-6 rounded shadow">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">현재 날씨 정보</h2>
          <button 
            onClick={fetchCurrentWeather}
            disabled={loadingWeather}
            className={`px-4 py-2 rounded transition ${loadingWeather ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
          >
            {loadingWeather ? '로딩 중...' : '새로고침'}
          </button>
        </div>
        
        {loadingWeather ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-blue-600">날씨 데이터를 불러오는 중...</p>
          </div>
        ) : !currentWeather ? (
          <div className="text-center py-8 text-gray-500">
            <p>날씨 데이터를 불러올 수 없습니다. '새로고침' 버튼을 눌러주세요.</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-lg font-semibold">{currentWeather.location}</h3>
              <p className="text-sm text-gray-500">
                {formatDate(currentWeather.date)} {formatTime(currentWeather.time)}
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-50 p-4 rounded">
                <h4 className="text-sm font-medium text-gray-500">기온</h4>
                <p className="text-2xl font-bold">{currentWeather.weather.temperature}°C</p>
              </div>
              
              <div className="bg-blue-50 p-4 rounded">
                <h4 className="text-sm font-medium text-gray-500">습도</h4>
                <p className="text-2xl font-bold">{currentWeather.weather.humidity}%</p>
              </div>
              
              <div className="bg-blue-50 p-4 rounded">
                <h4 className="text-sm font-medium text-gray-500">강수량</h4>
                <p className="text-2xl font-bold">{currentWeather.weather.rainfall}mm</p>
              </div>
              
              <div className="bg-blue-50 p-4 rounded">
                <h4 className="text-sm font-medium text-gray-500">풍속</h4>
                <p className="text-2xl font-bold">{currentWeather.weather.windSpeed}m/s</p>
              </div>
            </div>
            
            {currentWeather.weather.precipitationType && (
              <div className="bg-gray-100 p-4 rounded">
                <h4 className="text-sm font-medium text-gray-500">강수 형태</h4>
                <p className="text-xl font-bold">{currentWeather.weather.precipitationType}</p>
              </div>
            )}
            
            <button
              onClick={handlePredictWithCurrentWeather}
              disabled={loading}
              className={`w-full py-2 px-4 rounded transition ${loading ? 'bg-gray-400' : 'bg-green-600 text-white hover:bg-green-700'}`}
            >
              {loading ? '예측 중...' : '현재 날씨로 풍속 예측하기'}
            </button>
          </div>
        )}
        
        <div className="mt-4">
          <h3 className="text-lg font-semibold mb-2">API 키 테스트</h3>
          <button 
            onClick={testApiKey}
            disabled={loadingWeather}
            className={`px-4 py-2 rounded transition ${loadingWeather ? 'bg-gray-400' : 'bg-yellow-600 text-white hover:bg-yellow-700'}`}
          >
            API 키 테스트
          </button>
          
          {apiKeyTestResult && (
            <div className={`mt-2 p-3 rounded ${apiKeyTestResult.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              <p><strong>상태:</strong> {apiKeyTestResult.status}</p>
              <p><strong>메시지:</strong> {apiKeyTestResult.message}</p>
              {apiKeyTestResult.resultCode && (
                <p><strong>결과 코드:</strong> {apiKeyTestResult.resultCode}</p>
              )}
              {apiKeyTestResult.resultMsg && (
                <p><strong>결과 메시지:</strong> {apiKeyTestResult.resultMsg}</p>
              )}
            </div>
          )}
        </div>
        
        {error && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}
      </div>
      
      {/* 예측 결과 */}
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-semibold mb-4">예측 결과</h2>
        
        {prediction === null ? (
          <div className="text-center py-8 text-gray-500">
            <p>왼쪽에서 '현재 날씨로 풍속 예측하기' 버튼을 눌러주세요.</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="text-center">
              <div className="text-5xl font-bold text-blue-600">
                {prediction.predicted_wind_speed.toFixed(2)} <span className="text-2xl">m/s</span>
              </div>
              <p className="mt-2 text-gray-600">예측 평균 풍속</p>
              <div className="mt-1 text-sm text-gray-500">
                신뢰도: {(prediction.confidence * 100).toFixed(0)}% | 처리 시간: {prediction.execution_time.toFixed(3)}초
              </div>
            </div>
            
            <div className="bg-gray-100 p-4 rounded">
              <h3 className="font-semibold">풍속 단계</h3>
              <div className="mt-2">
                <div className="text-xl font-bold">{prediction.wind_level}</div>
                <p className="text-gray-600">{prediction.wind_description}</p>
              </div>
            </div>
            
            {currentWeather && currentWeather.weather.windSpeed && (
              <div className="bg-yellow-50 p-4 rounded">
                <h3 className="font-semibold">실제 관측 풍속</h3>
                <div className="mt-2">
                  <div className="text-xl font-bold">{currentWeather.weather.windSpeed} m/s</div>
                  <p className="text-gray-600">{getWindLevel(currentWeather.weather.windSpeed).level}</p>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  <p>예측값과 실제값 차이: {Math.abs(prediction.predicted_wind_speed - currentWeather.weather.windSpeed).toFixed(2)} m/s</p>
                </div>
              </div>
            )}
            
            {prediction.feature_importance && (
              <div>
                <h3 className="font-semibold mb-2">특성 중요도</h3>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.entries(prediction.feature_importance)
                        .map(([feature, importance]) => ({ feature, importance: Math.abs(importance) }))
                        .sort((a, b) => b.importance - a.importance)}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis dataKey="feature" type="category" width={100} />
                      <Tooltip formatter={(value) => [value.toFixed(4), '중요도']} />
                      <Bar dataKey="importance" fill="#8884d8" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            
            <div className="text-sm text-gray-500 mt-2">
              <p>* 이 예측은 모델을 기반으로 하며, 실제 기상 조건과 차이가 있을 수 있습니다.</p>
              <p>* 실시간 날씨 데이터는 기상청 API를 통해 제공됩니다.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // 모델 훈련 탭 렌더링
  const renderTrainTab = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* 파일 업로드 */}
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-semibold mb-4">데이터 파일 업로드</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">풍속 데이터 파일 (CSV)</label>
            <div className="flex space-x-2">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileChange(e, 'wind')}
                className="flex-grow p-2 border rounded"
              />
              <button
                onClick={() => handleFileUpload('wind')}
                disabled={loading || !files.wind}
                className={`px-4 rounded transition ${loading || !files.wind ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
              >
                업로드
              </button>
            </div>
            {uploadStatus.wind && (
              <div className="mt-1 text-sm text-green-600">
                ✓ 업로드 완료
              </div>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">습도 데이터 파일 (CSV)</label>
            <div className="flex space-x-2">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileChange(e, 'humidity')}
                className="flex-grow p-2 border rounded"
              />
              <button
                onClick={() => handleFileUpload('humidity')}
                disabled={loading || !files.humidity}
                className={`px-4 rounded transition ${loading || !files.humidity ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
              >
                업로드
              </button>
            </div>
            {uploadStatus.humidity && (
              <div className="mt-1 text-sm text-green-600">
                ✓ 업로드 완료
              </div>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">온도 데이터 파일 (CSV)</label>
            <div className="flex space-x-2">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileChange(e, 'temp')}
                className="flex-grow p-2 border rounded"
              />
              <button
                onClick={() => handleFileUpload('temp')}
                disabled={loading || !files.temp}
                className={`px-4 rounded transition ${loading || !files.temp ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
              >
                업로드
              </button>
            </div>
            {uploadStatus.temp && (
              <div className="mt-1 text-sm text-green-600">
                ✓ 업로드 완료
              </div>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">강수량 데이터 파일 (CSV)</label>
            <div className="flex space-x-2">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileChange(e, 'rain')}
                className="flex-grow p-2 border rounded"
              />
              <button
                onClick={() => handleFileUpload('rain')}
                disabled={loading || !files.rain}
                className={`px-4 rounded transition ${loading || !files.rain ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
              >
                업로드
              </button>
            </div>
            {uploadStatus.rain && (
              <div className="mt-1 text-sm text-green-600">
                ✓ 업로드 완료
              </div>
            )}
          </div>
        </div>
        
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-2">훈련 설정</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">테스트 세트 비율</label>
              <input
                type="range"
                name="testSize"
                min="0.1"
                max="0.5"
                step="0.05"
                value={trainingParams.testSize}
                onChange={handleTrainingParamChange}
                className="w-full"
              />
              <div className="flex justify-between text-sm">
                <span>10%</span>
                <span>{trainingParams.testSize * 100}%</span>
                <span>50%</span>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">정규화 계수 (Alpha)</label>
              <input
                type="range"
                name="alpha"
                min="0.01"
                max="1"
                step="0.01"
                value={trainingParams.alpha}
                onChange={handleTrainingParamChange}
                className="w-full"
              />
              <div className="flex justify-between text-sm">
                <span>0.01</span>
                <span>{trainingParams.alpha}</span>
                <span>1.0</span>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">다항식 차수</label>
              <select
                name="polynomialDegree"
                value={trainingParams.polynomialDegree}
                onChange={handleTrainingParamChange}
                className="w-full p-2 border rounded"
              >
                <option value={1}>1차 (선형)</option>
                <option value={2}>2차 (이차)</option>
                <option value={3}>3차 (삼차)</option>
              </select>
            </div>
            
            <button
              onClick={handleTrainModel}
              disabled={loading || Object.values(uploadStatus).some(status => status === null)}
              className={`w-full py-2 px-4 rounded transition ${loading || Object.values(uploadStatus).some(status => status === null) ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
            >
              {loading ? '처리 중...' : '모델 훈련 시작'}
            </button>
          </div>
        </div>
      </div>
      
      {/* 훈련 결과 */}
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-semibold mb-4">훈련 결과</h2>
        
        {!trainStatus ? (
          <div className="text-center py-8 text-gray-500">
            <p>왼쪽 폼에서 데이터 파일을 업로드하고 모델 훈련을 시작하세요.</p>
          </div>
        ) : trainStatus.status === 'training' || trainStatus.status === 'started' ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-blue-600">{trainStatus.message}</p>
            {trainStatus.model_id && (
              <p className="text-sm text-gray-500 mt-2">모델 ID: {trainStatus.model_id}</p>
            )}
          </div>
        ) : trainStatus.status === 'failed' ? (
          <div className="text-center py-8 text-red-600">
            <p>{trainStatus.message}</p>
          </div>
        ) : trainStatus.status === 'completed' && trainStatus.result ? (
          <div className="space-y-6">
            <div className="text-center text-green-600">
              <p className="text-xl">✓ 모델 훈련 완료</p>
              <p className="text-sm text-gray-500 mt-1">훈련 시간: {trainStatus.result.training_time.toFixed(2)}초</p>
            </div>
            
            <div>
              <h3 className="font-semibold mb-2">모델 성능</h3>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-blue-50 p-3 rounded">
                  <p className="text-sm font-medium">선형 모델</p>
                  <p className="text-lg font-bold">R² = {trainStatus.result.metrics.linear.r2.toFixed(4)}</p>
                  <p className="text-sm">RMSE = {trainStatus.result.metrics.linear.rmse.toFixed(4)}</p>
                </div>
                <div className="bg-green-50 p-3 rounded">
                  <p className="text-sm font-medium">다항식 모델</p>
                  <p className="text-lg font-bold">R² = {trainStatus.result.metrics.polynomial.r2.toFixed(4)}</p>
                  <p className="text-sm">RMSE = {trainStatus.result.metrics.polynomial.rmse.toFixed(4)}</p>
                </div>
              </div>
            </div>
            
            {trainStatus.result.feature_importance && (
              <div>
                <h3 className="font-semibold mb-2">특성 중요도</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={trainStatus.result.feature_importance}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis dataKey="feature" type="category" width={100} />
                      <Tooltip formatter={(value) => [value.toFixed(4), '중요도']} />
                      <Bar dataKey="importance" fill="#8884d8" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            
            {trainStatus.result.sample_predictions && (
              <div>
                <h3 className="font-semibold mb-2">샘플 예측 결과</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full bg-white border">
                    <thead>
                      <tr>
                        <th className="py-2 px-4 border-b">실제 값</th>
                        <th className="py-2 px-4 border-b">선형 예측</th>
                        <th className="py-2 px-4 border-b">다항식 예측</th>
                        <th className="py-2 px-4 border-b">선형 오차</th>
                        <th className="py-2 px-4 border-b">다항식 오차</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trainStatus.result.sample_predictions.map((pred, index) => (
                        <tr key={index}>
                          <td className="py-2 px-4 border-b">{pred.actual.toFixed(2)}</td>
                          <td className="py-2 px-4 border-b">{pred.linear_predicted.toFixed(2)}</td>
                          <td className="py-2 px-4 border-b">{pred.poly_predicted.toFixed(2)}</td>
                          <td className="py-2 px-4 border-b">{pred.linear_diff.toFixed(2)}</td>
                          <td className="py-2 px-4 border-b">{pred.poly_diff.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>훈련 상태를 가져올 수 없습니다.</p>
          </div>
        )}
        
        {error && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}
      </div>
    </div>
  );

  // 모델 관리 탭 렌더링
  const renderModelsTab = () => (
    <div className="bg-white p-6 rounded shadow">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">모델 목록</h2>
        <button 
          onClick={fetchModels}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          새로고침
        </button>
      </div>
      
      {models.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>저장된 모델이 없습니다. 모델 훈련 탭에서 모델을 훈련하세요.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border">
            <thead>
              <tr>
                <th className="py-2 px-4 border-b">모델 ID</th>
                <th className="py-2 px-4 border-b">생성 시간</th>
                <th className="py-2 px-4 border-b">선형 R²</th>
                <th className="py-2 px-4 border-b">다항식 R²</th>
                <th className="py-2 px-4 border-b">특성 수</th>
                <th className="py-2 px-4 border-b">작업</th>
              </tr>
            </thead>
            <tbody>
              {models.map(model => (
                <tr key={model.model_id}>
                  <td className="py-2 px-4 border-b">{model.model_id}</td>
                  <td className="py-2 px-4 border-b">{model.created_at}</td>
                  <td className="py-2 px-4 border-b">{model.metrics?.linear?.r2.toFixed(4) || 'N/A'}</td>
                  <td className="py-2 px-4 border-b">{model.metrics?.polynomial?.r2.toFixed(4) || 'N/A'}</td>
                  <td className="py-2 px-4 border-b">{model.feature_names?.length || 'N/A'}</td>
                  <td className="py-2 px-4 border-b">
                    <button 
                      onClick={() => {
                        handleModelSelect(model.model_id);
                        setActiveTab('predict');
                      }}
                      className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition"
                    >
                      선택
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  // 날씨 예보 탭 렌더링
  const renderForecastTab = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* 날씨 예보 정보 */}
      <div className="bg-white p-6 rounded shadow">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">예보 정보</h2>
          <button 
            onClick={fetchShortForecast}
            disabled={loadingWeather}
            className={`px-4 py-2 rounded transition ${loadingWeather ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
          >
            {loadingWeather ? '로딩 중...' : '예보 가져오기'}
          </button>
        </div>
        
        {loadingWeather ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-blue-600">예보 데이터를 불러오는 중...</p>
          </div>
        ) : !weatherForecast ? (
          <div className="text-center py-8 text-gray-500">
            <p>예보 데이터를 불러올 수 없습니다. '예보 가져오기' 버튼을 눌러주세요.</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-lg font-semibold">{weatherForecast.location}</h3>
              <p className="text-sm text-gray-500">
                기준: {formatDate(weatherForecast.baseDate)} {formatTime(weatherForecast.baseTime)}
              </p>
            </div>
            
            <div className="space-y-4">
              <h3 className="font-semibold">향후 예보</h3>
              
              {weatherForecast.forecasts.slice(0, 5).map((forecast, index) => (
                <div key={index} className="p-3 bg-blue-50 rounded">
                  <div className="flex justify-between">
                    <div>
                      <p className="font-medium">{formatDate(forecast.date)} {formatTime(forecast.time)}</p>
                    </div>
                    <div>
                      {forecast.weather.skyCondition && (
                        <span className="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">{forecast.weather.skyCondition}</span>
                      )}
                      {forecast.weather.precipitationType && forecast.weather.precipitationType !== '없음' && (
                        <span className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded ml-2">{forecast.weather.precipitationType}</span>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    <div>
                      <p className="text-xs text-gray-500">기온</p>
                      <p className="font-bold">{forecast.weather.temperature}°C</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">습도</p>
                      <p className="font-bold">{forecast.weather.humidity}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">강수확률</p>
                      <p className="font-bold">{forecast.weather.precipitationProbability}%</p>
                    </div>
                  </div>
                  <div className="mt-2">
                    <button
                      onClick={() => {
                        setForecastInputs({
                          date: formatDate(forecast.date),
                          location: weatherForecast.location,
                          avgHumidity: forecast.weather.humidity || 60,
                          avgTemp: forecast.weather.temperature || 20,
                          rainfallProb: forecast.weather.precipitationProbability || 0
                        });
                      }}
                      className="px-2 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition"
                    >
                      이 날씨로 예측하기
                    </button>
                  </div>
                </div>
              ))}
              
              {weatherForecast.forecasts.length > 5 && (
                <div className="text-center">
                  <p className="text-sm text-gray-500">총 {weatherForecast.forecasts.length}개의 예보 중 5개만 표시됩니다.</p>
                </div>
              )}
            </div>
          </div>
        )}
        
        {error && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}
      </div>
      
      {/* 예측 결과 */}
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-semibold mb-4">풍속 예측</h2>
        
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium mb-1">날짜</label>
            <input
              type="date"
              name="date"
              value={forecastInputs.date}
              onChange={handleForecastInputChange}
              className="w-full p-2 border rounded"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">지역</label>
            <input
              type="text"
              name="location"
              value={forecastInputs.location}
              onChange={handleForecastInputChange}
              className="w-full p-2 border rounded"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">예상 평균습도 (%rh)</label>
            <input
              type="range"
              name="avgHumidity"
              min="0"
              max="100"
              value={forecastInputs.avgHumidity}
              onChange={handleForecastInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>0</span>
              <span>{forecastInputs.avgHumidity}</span>
              <span>100</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">예상 평균기온 (℃)</label>
            <input
              type="range"
              name="avgTemp"
              min="-20"
              max="40"
              value={forecastInputs.avgTemp}
              onChange={handleForecastInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>-20</span>
              <span>{forecastInputs.avgTemp}</span>
              <span>40</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">강수 확률 (%)</label>
            <input
              type="range"
              name="rainfallProb"
              min="0"
              max="100"
              value={forecastInputs.rainfallProb}
              onChange={handleForecastInputChange}
              className="w-full"
            />
            <div className="flex justify-between text-sm">
              <span>0</span>
              <span>{forecastInputs.rainfallProb}</span>
              <span>100</span>
            </div>
          </div>
          
          <button
            onClick={handleForecast}
            disabled={loading}
            className={`w-full py-2 px-4 rounded transition ${loading ? 'bg-gray-400' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
          >
            {loading ? '예측 중...' : '풍속 예측하기'}
          </button>
        </div>
        
        {prediction && (
          <div className="space-y-6">
            <div className="text-center">
              <div className="text-2xl font-bold">
                {prediction.location || forecastInputs.location} - {prediction.forecast_date || forecastInputs.date}
              </div>
              <div className="text-5xl font-bold text-blue-600 mt-4">
                {prediction.predicted_wind_speed.toFixed(2)} <span className="text-2xl">m/s</span>
              </div>
              <p className="mt-2 text-gray-600">예측 평균 풍속</p>
            </div>
            
            <div className="bg-gray-100 p-4 rounded">
              <h3 className="font-semibold">풍속 단계</h3>
              <div className="mt-2">
                <div className="text-xl font-bold">{prediction.wind_level}</div>
                <p className="text-gray-600">{prediction.wind_description}</p>
              </div>
            </div>
            
            <div className="bg-blue-50 p-4 rounded">
              <h3 className="font-semibold">예보 조건</h3>
              <div className="mt-2 space-y-2">
                <p><span className="font-medium">평균 습도:</span> {forecastInputs.avgHumidity}%</p>
                <p><span className="font-medium">평균 기온:</span> {forecastInputs.avgTemp}°C</p>
                <p><span className="font-medium">강수 확률:</span> {forecastInputs.rainfallProb}%</p>
              </div>
            </div>
          </div>
        )}
        
        {error && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col p-6 max-w-6xl mx-auto bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-2 text-center text-gray-800">풍속 예측 시스템</h1>
      <p className="text-center text-gray-600 mb-6">기상청 API 연동 인천광역시 미추홀구 용현1.4동 날씨 기반</p>
      
      {renderTabs()}
      
      {activeTab === 'predict' && renderPredictTab()}
      {activeTab === 'realtime' && renderRealtimeTab()}
      {activeTab === 'train' && renderTrainTab()}
      {activeTab === 'models' && renderModelsTab()}
      {activeTab === 'forecast' && renderForecastTab()}
      
      <div className="mt-8 text-center text-gray-500 text-sm">
        <p>풍속 예측 시스템 v1.1.0 &copy; {new Date().getFullYear()} - 기상청 단기예보 API 활용</p>
      </div>
    </div>
  );
};

export default WindSpeedPredictor;