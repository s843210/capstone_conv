import React, {useState} from 'react';
import {
  SafeAreaView,
  Text,
  TextInput,
  Pressable,
  Alert,
  View,
  KeyboardAvoidingView,
  Platform,
  Image,
} from 'react-native';
import {LoginScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

type Props = LoginScreenProps & {
  loginUser: (name: string) => Promise<boolean>;
};

export default function LoginScreen({navigation, loginUser}: Props) {
  const [name, setName] = useState('');

  return (
    <SafeAreaView style={styles.loginPage}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.loginKeyboardWrap}>
        <View style={styles.loginContent}>
          <View style={styles.loginHeader}>
            <Text style={styles.loginAppTitle}>CoopsPick</Text>
            <Text style={styles.loginIntroText}>
              조선대학교 IT융합대학 5층 Coopsket 전용 앱입니다.
            </Text>
            <Text style={styles.loginDescription}>
              쿱스켓의 상품과 재고를 확인하고, 필요한 상품을 간편하게 요청해보세요.
            </Text>
          </View>

          <View style={styles.loginLogoWrap}>
            <Image
              source={require('../../assets/images/chosunlogo.png')}
              style={styles.loginLogo}
              resizeMode="contain"
            />
          </View>

          <View style={styles.loginCard}>
            <TextInput
              placeholder="아이디를 입력하세요"
              placeholderTextColor="rgba(255,255,255,0.72)"
              value={name}
              onChangeText={setName}
              style={styles.loginInput}
            />
            <TextInput
              placeholder="비밀번호를 입력하세요"
              placeholderTextColor="rgba(255,255,255,0.72)"
              secureTextEntry
              style={styles.loginInput}
            />
            <Pressable
              style={styles.loginPrimaryBtn}
              onPress={async () => {
                const trimmedName = name.trim();
                if (!trimmedName) {
                  Alert.alert('입력 필요', '이름 또는 학번을 입력해 주세요.');
                  return;
                }
                if (trimmedName.length < 2) {
                  Alert.alert('입력 오류', '이름 또는 학번을 2자 이상 입력해 주세요.');
                  return;
                }

                const saved = await loginUser(trimmedName);
                if (!saved) {
                  Alert.alert('로그인 오류', '사용자 정보를 저장하지 못했습니다. 다시 시도해 주세요.');
                  return;
                }

                navigation.replace('ProductList');
              }}>
              <Text style={styles.loginPrimaryBtnText}>로그인하기</Text>
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}


